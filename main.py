# ===============================================
# TURBO PHOTO SORTER v3.0 — Enhanced UI/UX Edition
# Features:
# 1. Zero-Lag Multithreaded Loading
# 2. Non-Destructive Brightness & Contrast
# 3. Saves Modified Images to separate folders
# 4. Modern UI with Filmstrip Preview
# 5. Drag & Drop Support
# 6. Fullscreen Mode
# 7. Mouse Wheel Zoom
# 8. Keyboard Shortcut Hints
# ===============================================

import os
import json
import shutil
import threading
import queue
import math
from tkinter import (
    Tk, Canvas, Frame, Label, Button, Text,
    filedialog, messagebox, ttk, Scale, HORIZONTAL, Toplevel
)
import exifread
from PIL import Image, ImageTk, ImageOps, ImageEnhance

# ───── Config ─────
CONFIG_FILE = "turbo_sorter_config.json"
LOG_FILE_NAME = "turbo_sorter_log.json"

THEMES = {
    "dark": {
        "bg": "#0d1117", "fg": "#e6edf3", "panel": "#161b22",
        "keep": "#238636", "discard": "#da3633", "maybe": "#d29922",
        "highlight": "#1f6feb", "text_dim": "#8b949e",
        "exif_bg": "#0d1117", "exif_fg": "#8b949e", "btn_fg": "#ffffff",
        "border": "#30363d", "hover": "#1c2128", "filmstrip_bg": "#0d1117",
        "accent": "#58a6ff",
    },
    "light": {
        "bg": "#ffffff", "fg": "#1f2328", "panel": "#f6f8fa",
        "keep": "#2da44e", "discard": "#cf222e", "maybe": "#bf8700",
        "highlight": "#0969da", "text_dim": "#656d76",
        "exif_bg": "#f6f8fa", "exif_fg": "#656d76", "btn_fg": "#ffffff",
        "border": "#d0d7de", "hover": "#eaeef2", "filmstrip_bg": "#f6f8fa",
        "accent": "#0969da",
    }
}


class ImageLoader:
    """
    Handles heavy lifting (Disk I/O, Resize, Rotate, Exif) 
    in a background thread to prevent UI freezing.
    """
    @staticmethod
    def load_and_process(path, target_width, target_height):
        try:
            # 1. Read EXIF (Disk I/O)
            exif_text = ""
            try:
                with open(path, 'rb') as f:
                    tags = exifread.process_file(f, details=False)
                if tags:
                    interesting = ['Image Make', 'Image Model', 'EXIF DateTimeOriginal', 
                                   'EXIF FNumber', 'EXIF ExposureTime', 'EXIF ISOSpeedRatings',
                                   'EXIF FocalLength', 'EXIF Flash']
                    for tag in interesting:
                        if tag in tags:
                            clean_tag = tag.replace("Image ", "").replace("EXIF ", "")
                            exif_text += f"{clean_tag:<18}: {tags[tag]}\n"
                else:
                    exif_text = "No EXIF Data"
            except:
                exif_text = "EXIF Error"

            # 2. Load Image (Disk I/O)
            img = Image.open(path)
            
            # 3. Rotate (CPU Intensive)
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")

            # 4. Smart Resize (CPU Intensive)
            ratio = min(target_width / img.width, target_height / img.height) * 0.99
            new_w = int(img.width * ratio)
            new_h = int(img.height * ratio)
            
            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            return resized_img, exif_text
            
        except Exception as e:
            print(f"Loader Error: {e}")
            return None, str(e)

    @staticmethod
    def load_thumbnail(path, thumb_size=120):
        """Load a small thumbnail for the filmstrip."""
        try:
            img = Image.open(path)
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
            return img
        except:
            return None


class TurboSorter:
    def __init__(self, root):
        self.root = root
        self.root.title("Turbo Photo Sorter v3.0")
        self.root.geometry("1600x1000")
        self.root.minsize(1200, 700)

        # State
        self.source_dir = ""
        self.keep_dir = self.discard_dir = self.maybe_dir = ""
        self.keep_mod_dir = self.discard_mod_dir = self.maybe_mod_dir = ""
        
        self.image_list = []
        self.current_index = 0
        self.history = []
        self.processed_files = set()
        
        # Caching / Threading State
        self.cache = {}
        self.thumb_cache = {}
        self.load_queue = queue.Queue()
        self.thumb_load_queue = queue.Queue()
        self.canvas_dim = (1200, 900)
        
        # Display State
        self.base_image = None
        self.photo_ref = None
        self.brightness_val = 1.0
        self.contrast_val = 1.0

        # Zoom State
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Fullscreen State
        self.is_fullscreen = False
        self.fullscreen_window = None

        self.dark_mode = True
        self.colors = THEMES["dark"]

        self.load_config()
        self.build_ui()
        self.bind_keys()
        
        # Start queue listeners
        self.check_queue()
        self.check_thumb_queue()

    def build_ui(self):
        self.root.configure(bg=self.colors["bg"])
        
        # Main layout: 3 rows (canvas, filmstrip, status)
        self.root.grid_rowconfigure(0, weight=1)  # Canvas area
        self.root.grid_rowconfigure(1, weight=0)  # Filmstrip
        self.root.grid_rowconfigure(2, weight=0)  # Status bar
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, minsize=320, weight=0)

        # --- 1. Main Canvas (Left) ---
        canvas_frame = Frame(self.root, bg=self.colors["bg"], 
                             highlightbackground=self.colors["border"], highlightthickness=1)
        canvas_frame.grid(row=0, column=0, sticky="nsew", padx=(5, 2), pady=(5, 2))
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas = Canvas(canvas_frame, bg=self.colors["bg"], highlightthickness=0, cursor="crosshair")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self.on_resize)

        self.placeholder = Label(self.canvas, text="📁  Click or Drag Folder Here\n\nPress Ctrl+O to open",
                                 font=("Segoe UI", 20), bg=self.colors["bg"], fg=self.colors["text_dim"],
                                 justify="center")
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        self.loading_label = Label(self.canvas, text="⏳ LOADING...", 
                                   font=("Segoe UI", 36, "bold"), bg=self.colors["bg"], fg=self.colors["highlight"])
        self.loading_label.place_forget()

        # --- 2. Sidebar (Right) ---
        self.sidebar = Frame(self.root, bg=self.colors["panel"], 
                             highlightbackground=self.colors["border"], highlightthickness=1)
        self.sidebar.grid(row=0, column=1, sticky="nsew", padx=(2, 5), pady=(5, 2))
        self.sidebar.pack_propagate(False)

        # Padding container
        pad = Frame(self.sidebar, bg=self.colors["panel"])
        pad.pack(fill="both", expand=True, padx=15, pady=15)

        # --- Header with Theme Toggle ---
        header_frame = Frame(pad, bg=self.colors["panel"])
        header_frame.pack(fill="x", pady=(0, 10))

        self.theme_btn = Button(header_frame, text="🌙" if self.dark_mode else "☀️", 
                                command=self.toggle_theme,
                                bg=self.colors["panel"], fg=self.colors["fg"], 
                                relief="flat", font=("Segoe UI", 14), cursor="hand2",
                                activebackground=self.colors["hover"], activeforeground=self.colors["accent"])
        self.theme_btn.pack(side="left")

        # Progress Stats
        self.progress_text = Label(header_frame, text="0 / 0", font=("Segoe UI", 18, "bold"),
                                   bg=self.colors["panel"], fg=self.colors["fg"])
        self.progress_text.pack(side="right")

        # Progress Bar
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", 
                       background=self.colors["highlight"],
                       troughcolor=self.colors["bg"],
                       bordercolor=self.colors["border"],
                       lightcolor=self.colors["highlight"],
                       darkcolor=self.colors["highlight"])
        self.progress_bar = ttk.Progressbar(pad, mode="determinate", style="TProgressbar")
        self.progress_bar.pack(fill="x", pady=(0, 15))

        # Status / Action Label
        self.lbl_action = Label(pad, text="Ready", font=("Segoe UI", 13, "bold"),
                                bg=self.colors["panel"], fg=self.colors["text_dim"], anchor="center")
        self.lbl_action.pack(fill="x", pady=(0, 15))

        # --- Image Adjustments Frame ---
        adj_frame = Frame(pad, bg=self.colors["panel"], 
                          highlightbackground=self.colors["border"], highlightthickness=1, padx=10, pady=10)
        adj_frame.pack(fill="x", pady=(0, 15))

        Label(adj_frame, text="🎨 Adjustments", font=("Segoe UI", 10, "bold"),
              bg=self.colors["panel"], fg=self.colors["fg"]).pack(anchor="w", pady=(0, 8))
        
        # Brightness
        bright_frame = Frame(adj_frame, bg=self.colors["panel"])
        bright_frame.pack(fill="x", pady=(0, 8))
        Label(bright_frame, text="☀ Brightness", 
              bg=self.colors["panel"], fg=self.colors["text_dim"], font=("Segoe UI", 9)).pack(anchor="w")
        self.scale_bright = Scale(bright_frame, from_=0.5, to=3.0, resolution=0.1, 
                                  orient=HORIZONTAL, command=self.on_brightness_change,
                                  bg=self.colors["panel"], fg=self.colors["fg"], 
                                  highlightthickness=0, troughcolor=self.colors["bg"], 
                                  activebackground=self.colors["highlight"],
                                  length=250, sliderrelief="flat")
        self.scale_bright.set(1.0)
        self.scale_bright.pack(fill="x")

        # Contrast
        contrast_frame = Frame(adj_frame, bg=self.colors["panel"])
        contrast_frame.pack(fill="x", pady=(0, 8))
        Label(contrast_frame, text="🌓 Contrast", 
              bg=self.colors["panel"], fg=self.colors["text_dim"], font=("Segoe UI", 9)).pack(anchor="w")
        self.scale_contrast = Scale(contrast_frame, from_=0.5, to=3.0, resolution=0.1, 
                                    orient=HORIZONTAL, command=self.on_contrast_change,
                                    bg=self.colors["panel"], fg=self.colors["fg"], 
                                    highlightthickness=0, troughcolor=self.colors["bg"], 
                                    activebackground=self.colors["highlight"],
                                    length=250, sliderrelief="flat")
        self.scale_contrast.set(1.0)
        self.scale_contrast.pack(fill="x")
        
        btn_reset = Button(adj_frame, text="↺ Reset Adjustments", command=self.reset_adjustments,
                           bg=self.colors["bg"], fg=self.colors["fg"], relief="flat", 
                           font=("Segoe UI", 9), cursor="hand2",
                           activebackground=self.colors["hover"], activeforeground=self.colors["accent"])
        btn_reset.pack(fill="x", pady=(5, 0))

        # --- Action Buttons ---
        btn_frame = Frame(pad, bg=self.colors["panel"])
        btn_frame.pack(fill="x", pady=(0, 15))

        self.btn_keep = self.mk_btn(btn_frame, "✓  KEEP", self.colors["keep"], 
                                    lambda: self.sort("keep"), "→ / K / Space")
        self.btn_discard = self.mk_btn(btn_frame, "✗  DISCARD", self.colors["discard"], 
                                       lambda: self.sort("discard"), "↓ / N")
        self.btn_maybe = self.mk_btn(btn_frame, "?  MAYBE", self.colors["maybe"], 
                                     lambda: self.sort("maybe"), "M")
        self.btn_undo = self.mk_btn(btn_frame, "↩  UNDO", "#555", self.undo, "Ctrl+Z")

        # --- Zoom Controls ---
        zoom_frame = Frame(pad, bg=self.colors["panel"])
        zoom_frame.pack(fill="x", pady=(0, 15))
        
        Label(zoom_frame, text="🔍 Zoom", font=("Segoe UI", 10, "bold"),
              bg=self.colors["panel"], fg=self.colors["fg"]).pack(anchor="w", pady=(0, 5))
        
        zoom_btn_frame = Frame(zoom_frame, bg=self.colors["panel"])
        zoom_btn_frame.pack(fill="x")
        
        self.btn_zoom_in = Button(zoom_btn_frame, text="➕  Zoom In", command=self.zoom_in,
                                  bg=self.colors["bg"], fg=self.colors["fg"], relief="flat",
                                  font=("Segoe UI", 9), cursor="hand2",
                                  activebackground=self.colors["hover"], activeforeground=self.colors["accent"])
        self.btn_zoom_in.pack(side="left", fill="x", expand=True, padx=(0, 3))
        
        self.btn_zoom_out = Button(zoom_btn_frame, text="➖  Zoom Out", command=self.zoom_out,
                                   bg=self.colors["bg"], fg=self.colors["fg"], relief="flat",
                                   font=("Segoe UI", 9), cursor="hand2",
                                   activebackground=self.colors["hover"], activeforeground=self.colors["accent"])
        self.btn_zoom_out.pack(side="left", fill="x", expand=True, padx=(3, 3))
        
        self.btn_zoom_reset = Button(zoom_btn_frame, text="↺  Reset", command=self.zoom_reset,
                                     bg=self.colors["bg"], fg=self.colors["fg"], relief="flat",
                                     font=("Segoe UI", 9), cursor="hand2",
                                     activebackground=self.colors["hover"], activeforeground=self.colors["accent"])
        self.btn_zoom_reset.pack(side="left", fill="x", expand=True, padx=(3, 0))

        # --- Fullscreen Button ---
        self.btn_fullscreen = Button(pad, text="⛶  Fullscreen (F11)", command=self.toggle_fullscreen,
                                     bg=self.colors["bg"], fg=self.colors["fg"], relief="flat",
                                     font=("Segoe UI", 9), cursor="hand2",
                                     activebackground=self.colors["hover"], activeforeground=self.colors["accent"])
        self.btn_fullscreen.pack(fill="x", pady=(0, 15))

        # --- EXIF / Metadata ---
        lbl_info = Label(pad, text="📋 Metadata", font=("Segoe UI", 10, "bold"),
                         bg=self.colors["panel"], fg=self.colors["fg"], anchor="w")
        lbl_info.pack(fill="x", pady=(0, 5))
        
        self.exif_box = Text(pad, height=10, font=("Consolas", 9),
                             bg=self.colors["exif_bg"], fg=self.colors["exif_fg"],
                             relief="flat", highlightthickness=1, 
                             highlightbackground=self.colors["border"],
                             padx=8, pady=8)
        self.exif_box.pack(fill="both", expand=True)

        # --- 3. Filmstrip (Bottom) ---
        self.filmstrip_frame = Frame(self.root, bg=self.colors["filmstrip_bg"], 
                                     highlightbackground=self.colors["border"], highlightthickness=1,
                                     height=100)
        self.filmstrip_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 2))
        self.filmstrip_frame.grid_propagate(False)

        # Filmstrip canvas for scrolling
        self.filmstrip_canvas = Canvas(self.filmstrip_frame, bg=self.colors["filmstrip_bg"], 
                                       highlightthickness=0, height=90)
        self.filmstrip_canvas.pack(side="left", fill="both", expand=True)

        # Filmstrip scrollbar
        self.filmstrip_scrollbar = ttk.Scrollbar(self.filmstrip_frame, orient="horizontal", 
                                                  command=self.filmstrip_canvas.xview)
        self.filmstrip_scrollbar.pack(side="bottom", fill="x")
        self.filmstrip_canvas.configure(xscrollcommand=self.filmstrip_scrollbar.set)

        self.filmstrip_inner = Frame(self.filmstrip_canvas, bg=self.colors["filmstrip_bg"])
        self.filmstrip_canvas.create_window((0, 0), window=self.filmstrip_inner, anchor="nw")

        self.filmstrip_thumb_refs = []  # Keep references to prevent garbage collection

        # --- 4. Status Bar ---
        self.status_bar = Frame(self.root, bg=self.colors["panel"], height=24,
                                highlightbackground=self.colors["border"], highlightthickness=1)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 5))
        self.status_bar.grid_propagate(False)

        self.status_label = Label(self.status_bar, text="Ready — Click to load a folder or press Ctrl+O",
                                  bg=self.colors["panel"], fg=self.colors["text_dim"],
                                  font=("Segoe UI", 9), anchor="w", padx=10)
        self.status_label.pack(side="left", fill="x", expand=True)

        self.filename_label = Label(self.status_bar, text="", bg=self.colors["panel"], 
                                    fg=self.colors["text_dim"], font=("Segoe UI", 9), anchor="e", padx=10)
        self.filename_label.pack(side="right")

        # Setup interactions
        self.setup_interactions()

    def setup_interactions(self):
        """Setup mouse interactions for the canvas."""
        # Mouse wheel zoom
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        
        # Pan support with middle mouse button
        self.canvas.bind("<ButtonPress-2>", self.on_pan_start)
        self.canvas.bind("<B2-Motion>", self.on_pan_move)
        self.canvas.bind("<ButtonRelease-2>", self.on_pan_end)
        
        # Pan support with right mouse button
        self.canvas.bind("<ButtonPress-3>", self.on_pan_start)
        self.canvas.bind("<B3-Motion>", self.on_pan_move)
        self.canvas.bind("<ButtonRelease-3>", self.on_pan_end)

    def on_mousewheel(self, event):
        """Handle mouse wheel for zoom."""
        if not self.base_image:
            return
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def on_pan_start(self, event):
        """Start panning."""
        if self.zoom_level != 1.0:
            self.is_dragging = True
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.canvas.config(cursor="fleur")

    def on_pan_move(self, event):
        """Handle panning."""
        if self.is_dragging:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            self.pan_x += dx
            self.pan_y += dy
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            if self.base_image:
                self.refresh_image_visuals()

    def on_pan_end(self, event):
        """End panning."""
        self.is_dragging = False
        self.canvas.config(cursor="crosshair")

    def zoom_in(self):
        if self.zoom_level < 5.0:
            self.zoom_level = min(5.0, self.zoom_level * 1.25)
            if self.base_image:
                self.refresh_image_visuals()
            self.update_status("Zoom: {:.0f}%".format(self.zoom_level * 100))

    def zoom_out(self):
        if self.zoom_level > 0.2:
            self.zoom_level = max(0.2, self.zoom_level / 1.25)
            if self.base_image:
                self.refresh_image_visuals()
            self.update_status("Zoom: {:.0f}%".format(self.zoom_level * 100))

    def zoom_reset(self):
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        if self.base_image:
            self.refresh_image_visuals()
        self.update_status("Zoom reset")

    def mk_btn(self, parent, text, color, cmd, shortcut=""):
        """Create a styled button with shortcut hint."""
        frame = Frame(parent, bg=self.colors["panel"])
        frame.pack(fill="x", pady=3)
        
        b = Button(frame, text=text, command=cmd, bg=color, fg="#fff",
                   font=("Segoe UI", 11, "bold"), relief="flat", pady=10, cursor="hand2",
                   activebackground=self._lighten_color(color, 0.2))
        b.pack(fill="x", side="left", expand=True)
        
        if shortcut:
            hint = Label(frame, text=shortcut, bg=color, fg=self.colors["btn_fg"],
                         font=("Segoe UI", 8), padx=8)
            hint.pack(side="right")
        
        return b

    def _lighten_color(self, hex_color, factor=0.2):
        """Lighten a hex color by a factor."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c * 2 for c in hex_color)
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    def on_resize(self, event):
        self.canvas_dim = (event.width, event.height)

    # ───── ADJUSTMENT LOGIC ─────
    def on_brightness_change(self, val):
        self.brightness_val = float(val)
        if self.base_image:
            self.refresh_image_visuals()

    def on_contrast_change(self, val):
        self.contrast_val = float(val)
        if self.base_image:
            self.refresh_image_visuals()

    def reset_adjustments(self):
        self.scale_bright.set(1.0)
        self.scale_contrast.set(1.0)
        self.brightness_val = 1.0
        self.contrast_val = 1.0
        if self.base_image:
            self.refresh_image_visuals()
        self.update_status("Adjustments reset")

    def refresh_image_visuals(self):
        """Applies brightness, contrast, and zoom to the cached base image and updates canvas."""
        if not self.base_image:
            return

        img = self.base_image
        
        if self.brightness_val != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(self.brightness_val)
        
        if self.contrast_val != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(self.contrast_val)
        
        # Apply zoom
        if self.zoom_level != 1.0:
            new_w = int(img.width * self.zoom_level)
            new_h = int(img.height * self.zoom_level)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Display
        self.photo_ref = ImageTk.PhotoImage(img)
        self.canvas.delete("img_tag")
        
        cw, ch = self.canvas_dim
        cx = cw // 2 + self.pan_x
        cy = ch // 2 + self.pan_y
        self.canvas.create_image(cx, cy, image=self.photo_ref, anchor="center", tags="img_tag")
        self.canvas.tag_lower("img_tag")

    # ───── FULLSCREEN ─────
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self):
        """Enter fullscreen mode with a new window."""
        if not self.base_image:
            self.update_status("No image to display in fullscreen")
            return
        
        self.is_fullscreen = True
        self.btn_fullscreen.config(text="⛶  Exit Fullscreen (Esc)")
        
        # Create fullscreen window
        self.fullscreen_window = Toplevel(self.root)
        self.fullscreen_window.attributes("-fullscreen", True)
        self.fullscreen_window.configure(bg=self.colors["bg"])
        
        # Fullscreen canvas
        self.fs_canvas = Canvas(self.fullscreen_window, bg=self.colors["bg"], highlightthickness=0)
        self.fs_canvas.pack(fill="both", expand=True)
        
        # Display current image
        self.update_fullscreen_image()
        
        # Bind keys for fullscreen
        self.fullscreen_window.bind("<Escape>", lambda e: self.exit_fullscreen())
        self.fullscreen_window.bind("<F11>", lambda e: self.exit_fullscreen())
        self.fullscreen_window.bind("<Right>", lambda e: self.sort("keep"))
        self.fullscreen_window.bind("<Down>", lambda e: self.sort("discard"))
        self.fullscreen_window.bind("<m>", lambda e: self.sort("maybe"))
        self.fullscreen_window.bind("<Control-z>", lambda e: self.undo())
        self.fullscreen_window.bind("<MouseWheel>", self.on_fs_mousewheel)
        
        # Show overlay hints briefly
        self.show_fullscreen_hints()

    def update_fullscreen_image(self):
        """Update the fullscreen canvas with current image."""
        if not self.fullscreen_window or not self.base_image:
            return
        
        # Get fullscreen dimensions
        self.fs_canvas.update_idletasks()
        fw = self.fs_canvas.winfo_width()
        fh = self.fs_canvas.winfo_height()
        
        if fw < 10 or fh < 10:
            self.root.after(100, self.update_fullscreen_image)
            return
        
        # Load full-res image for fullscreen
        if self.current_index < len(self.image_list):
            path = os.path.join(self.source_dir, self.image_list[self.current_index])
            try:
                img = Image.open(path)
                img = ImageOps.exif_transpose(img)
                img = img.convert("RGB")
                
                # Apply adjustments
                if self.brightness_val != 1.0:
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(self.brightness_val)
                if self.contrast_val != 1.0:
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(self.contrast_val)
                
                # Resize to fit screen
                ratio = min(fw / img.width, fh / img.height) * 0.95
                new_w = int(img.width * ratio)
                new_h = int(img.height * ratio)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                self.fs_photo = ImageTk.PhotoImage(img)
                self.fs_canvas.delete("all")
                self.fs_canvas.create_image(fw // 2, fh // 2, image=self.fs_photo, anchor="center")
                
                # Show filename at bottom
                self.fs_canvas.create_text(
                    fw // 2, fh - 30,
                    text=f"{self.current_index + 1}/{len(self.image_list)} - {self.image_list[self.current_index]}",
                    fill=self.colors["text_dim"], font=("Segoe UI", 12)
                )
            except Exception as e:
                print(f"Fullscreen error: {e}")

    def show_fullscreen_hints(self):
        """Show temporary overlay hints in fullscreen."""
        if not self.fullscreen_window:
            return
        
        fw = self.fs_canvas.winfo_width()
        fh = self.fs_canvas.winfo_height()
        
        hints = [
            "→ / K: Keep    ↓ / N: Discard    M: Maybe    Ctrl+Z: Undo    Esc: Exit",
            "Mouse Wheel: Zoom"
        ]
        
        for i, hint in enumerate(hints):
            self.fs_canvas.create_text(
                fw // 2, 30 + i * 25,
                text=hint, fill=self.colors["text_dim"],
                font=("Segoe UI", 11), tags="hints"
            )
        
        # Remove hints after 3 seconds
        self.root.after(3000, lambda: self.fs_canvas.delete("hints"))

    def on_fs_mousewheel(self, event):
        """Handle mouse wheel in fullscreen."""
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def exit_fullscreen(self):
        """Exit fullscreen mode."""
        self.is_fullscreen = False
        self.btn_fullscreen.config(text="⛶  Fullscreen (F11)")
        if self.fullscreen_window:
            try:
                self.fullscreen_window.destroy()
            except:
                pass
            self.fullscreen_window = None
            self.fs_canvas = None

    # ───── LOADING ENGINE ─────
    def load_source(self, folder=None):
        if folder is None:
            folder = filedialog.askdirectory()
        if not folder:
            return
        
        self.source_dir = folder
        
        # Setup paths
        self.keep_dir = os.path.join(folder, "Keep")
        self.discard_dir = os.path.join(folder, "Discard")
        self.maybe_dir = os.path.join(folder, "Maybe")
        
        self.keep_mod_dir = os.path.join(folder, "Keep_Modified")
        self.discard_mod_dir = os.path.join(folder, "Discard_Modified")
        self.maybe_mod_dir = os.path.join(folder, "Maybe_Modified")

        for d in [self.keep_dir, self.discard_dir, self.maybe_dir, 
                  self.keep_mod_dir, self.discard_mod_dir, self.maybe_mod_dir]:
            os.makedirs(d, exist_ok=True)

        self.processed_log_file = os.path.join(self.source_dir, LOG_FILE_NAME)
        if os.path.exists(self.processed_log_file):
            try:
                with open(self.processed_log_file) as f:
                    self.processed_files = set(json.load(f).get("processed_files", []))
            except:
                self.processed_files = set()

        exts = (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".bmp")
        all_files = sorted([f for f in os.listdir(folder) if f.lower().endswith(exts)])
        self.image_list = [f for f in all_files if f not in self.processed_files]

        if not self.image_list:
            messagebox.showinfo("Done", "No new images found!")
            return

        self.current_index = 0
        self.cache.clear()
        self.thumb_cache.clear()
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.placeholder.place_forget()
        
        # Build filmstrip
        self.build_filmstrip()
        
        self.request_image(0)
        self.update_ui_text()
        self.update_status(f"Loaded {len(self.image_list)} images from {os.path.basename(folder)}")

    def build_filmstrip(self):
        """Build the thumbnail filmstrip at the bottom."""
        # Clear existing
        for w in self.filmstrip_inner.winfo_children():
            w.destroy()
        self.filmstrip_thumb_refs.clear()

        if not self.image_list:
            return

        # Load thumbnails in background
        for idx, filename in enumerate(self.image_list):
            path = os.path.join(self.source_dir, filename)
            threading.Thread(target=self.thumb_worker, args=(idx, path), daemon=True).start()

    def thumb_worker(self, idx, path):
        """Background thread for loading thumbnails."""
        thumb = ImageLoader.load_thumbnail(path, 100)
        if thumb:
            self.thumb_load_queue.put((idx, thumb))

    def check_thumb_queue(self):
        """Process thumbnail loading queue."""
        try:
            while True:
                idx, thumb = self.thumb_load_queue.get_nowait()
                self.thumb_cache[idx] = thumb
                self.add_thumb_to_filmstrip(idx, thumb)
        except queue.Empty:
            pass
        self.root.after(100, self.check_thumb_queue)

    def add_thumb_to_filmstrip(self, idx, thumb_img):
        """Add a thumbnail to the filmstrip UI."""
        try:
            photo = ImageTk.PhotoImage(thumb_img)
            self.filmstrip_thumb_refs.append(photo)
            
            # Create clickable thumbnail frame
            thumb_frame = Frame(self.filmstrip_inner, bg=self.colors["filmstrip_bg"], 
                               highlightbackground=self.colors["border"], highlightthickness=1,
                               padx=2, pady=2, cursor="hand2")
            
            lbl = Label(thumb_frame, image=photo, bg=self.colors["filmstrip_bg"])
            lbl.pack()
            
            # Highlight current image
            if idx == self.current_index:
                thumb_frame.config(highlightbackground=self.colors["highlight"], highlightthickness=2)
            
            # Click to navigate
            lbl.bind("<Button-1>", lambda e, i=idx: self.navigate_to(i))
            thumb_frame.bind("<Button-1>", lambda e, i=idx: self.navigate_to(i))
            
            thumb_frame.pack(side="left", padx=2)
            
            # Update scroll region
            self.filmstrip_inner.update_idletasks()
            self.filmstrip_canvas.configure(scrollregion=self.filmstrip_canvas.bbox("all"))
            
            # Scroll to current
            if idx == self.current_index:
                self.filmstrip_canvas.xview_moveto(max(0, (idx - 2) / max(1, len(self.image_list))))
                
        except Exception as e:
            print(f"Thumbnail display error: {e}")

    def navigate_to(self, idx):
        """Navigate to a specific image index."""
        if 0 <= idx < len(self.image_list):
            self.current_index = idx
            self.zoom_level = 1.0
            self.pan_x = 0
            self.pan_y = 0
            self.request_image(idx)
            self.update_ui_text()
            self.update_filmstrip_highlight()
            self.update_status(f"Image {idx + 1} of {len(self.image_list)}")

    def update_filmstrip_highlight(self):
        """Update the highlight on the filmstrip."""
        for i, child in enumerate(self.filmstrip_inner.winfo_children()):
            if i == self.current_index:
                child.config(highlightbackground=self.colors["highlight"], highlightthickness=2)
            else:
                child.config(highlightbackground=self.colors["border"], highlightthickness=1)

    def request_image(self, index):
        if index >= len(self.image_list):
            self.show_finished()
            return

        if index in self.cache:
            self.set_current_image_from_cache(self.cache[index])
            self.trigger_background_load(index + 1)
            self.trigger_background_load(index + 2)
        else:
            self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
            self.trigger_background_load(index, priority=True)

    def trigger_background_load(self, index, priority=False):
        if index >= len(self.image_list): return
        if index in self.cache: return
        
        path = os.path.join(self.source_dir, self.image_list[index])
        w, h = self.canvas_dim
        threading.Thread(target=self.background_worker, args=(index, path, w, h), daemon=True).start()

    def background_worker(self, index, path, w, h):
        img, exif = ImageLoader.load_and_process(path, w, h)
        self.load_queue.put((index, img, exif))

    def check_queue(self):
        try:
            while True:
                index, img, exif = self.load_queue.get_nowait()
                self.cache[index] = (img, exif)
                
                if index == self.current_index:
                    self.loading_label.place_forget()
                    self.set_current_image_from_cache((img, exif))
                    self.trigger_background_load(index + 1)
                    self.trigger_background_load(index + 2)
        except queue.Empty:
            pass
        self.root.after(50, self.check_queue)

    def set_current_image_from_cache(self, data):
        pil_img, exif_text = data
        self.base_image = pil_img
        
        # Display Info
        self.exif_box.config(state="normal")
        self.exif_box.delete(1.0, "end")
        self.exif_box.insert("end", self.image_list[self.current_index] + "\n" + ("-"*30) + "\n")
        self.exif_box.insert("end", exif_text)
        self.exif_box.config(state="disabled")

        # Update filename in status bar
        if self.current_index < len(self.image_list):
            self.filename_label.config(text=self.image_list[self.current_index])

        # Apply brightness and draw
        self.refresh_image_visuals()

    # ───── SORTING LOGIC ─────
    def sort(self, action):
        if self.current_index >= len(self.image_list): return

        filename = self.image_list[self.current_index]
        src = os.path.join(self.source_dir, filename)
        
        # Determine paths for original and modified
        target_dir = {
            "keep": self.keep_dir,
            "discard": self.discard_dir,
            "maybe": self.maybe_dir
        }[action]
        
        dst = os.path.join(target_dir, filename)

        # 1. Copy Original (Always)
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            print(f"Error copying: {e}")

        # 2. Save Modified (Only if brightness/contrast changed)
        if self.brightness_val != 1.0 or self.contrast_val != 1.0:
            target_mod_dir = {
                "keep": self.keep_mod_dir,
                "discard": self.discard_mod_dir,
                "maybe": self.maybe_mod_dir
            }[action]
            dst_mod = os.path.join(target_mod_dir, filename)
            
            # Use background thread to save full-res edited image to prevent UI lag
            threading.Thread(target=self.save_modified_worker, 
                             args=(src, dst_mod, self.brightness_val, self.contrast_val), 
                             daemon=True).start()

        self.history.append({"file": filename, "action": action, "src": src, "dst": dst})
        self.processed_files.add(filename)
        self.save_log()

        color = self.colors[action]
        self.lbl_action.config(text=f"{action.upper()}", fg=color)
        self.flash_overlay(action.upper(), color)

        if (self.current_index - 2) in self.cache:
            del self.cache[self.current_index - 2]

        self.current_index += 1
        self.update_ui_text()
        self.update_filmstrip_highlight()
        self.request_image(self.current_index)
        self.update_status(f"{action.upper()} → {filename}")
        
    def save_modified_worker(self, src, dst, brightness, contrast):
        """Re-opens the original file, modifies it, and saves it (Background Thread)."""
        try:
            # Re-open original to maintain resolution
            img = Image.open(src)
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            
            # Apply modifications
            if brightness != 1.0:
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(brightness)
            
            if contrast != 1.0:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(contrast)
            
            # Save
            img.save(dst, quality=95)
        except Exception as e:
            print(f"Failed to save modified image: {e}")

    def undo(self):
        if not self.history: return
        last = self.history.pop()
        
        if last["file"] in self.processed_files:
            self.processed_files.remove(last["file"])
            self.save_log()

        self.current_index -= 1
        self.lbl_action.config(text="UNDO", fg=self.colors["highlight"])
        self.update_ui_text()
        self.update_filmstrip_highlight()
        self.request_image(self.current_index)
        self.update_status(f"Undo: {last['file']}")

    def flash_overlay(self, text, color):
        w = self.canvas.winfo_width()
        tag = self.canvas.create_text(w//2, 100, text=text, fill=color, 
                                      font=("Segoe UI", 60, "bold"))
        self.root.after(400, lambda: self.canvas.delete(tag))

    def update_ui_text(self):
        self.progress_text.config(text=f"{self.current_index} / {len(self.image_list)}")
        if len(self.image_list) > 0:
            self.progress_bar["maximum"] = len(self.image_list)
            self.progress_bar["value"] = self.current_index

    def update_status(self, message):
        """Update the status bar message."""
        self.status_label.config(text=message)

    def show_finished(self):
        self.canvas.delete("all")
        self.canvas.create_text(
            self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2 - 30,
            text="🎉 ALL DONE!", font=("Segoe UI", 50, "bold"),
            fill=self.colors["keep"], anchor="center"
        )
        self.canvas.create_text(
            self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2 + 40,
            text=f"{len(self.image_list)} images processed",
            font=("Segoe UI", 18), fill=self.colors["text_dim"], anchor="center"
        )
        self.update_status("All images processed!")

    def save_log(self):
        with open(self.processed_log_file, "w") as f:
            json.dump({"processed_files": list(self.processed_files)}, f)

    def bind_keys(self):
        self.root.bind("<Right>", lambda e: self.sort("keep"))
        self.root.bind("<k>", lambda e: self.sort("keep"))
        self.root.bind("<space>", lambda e: self.sort("keep"))
        self.root.bind("<Down>", lambda e: self.sort("discard"))
        self.root.bind("<n>", lambda e: self.sort("discard"))
        self.root.bind("<m>", lambda e: self.sort("maybe"))
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-o>", lambda e: self.load_source())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<plus>", lambda e: self.zoom_in())
        self.root.bind("<equal>", lambda e: self.zoom_in())
        self.root.bind("<minus>", lambda e: self.zoom_out())
        self.root.bind("<Key-0>", lambda e: self.zoom_reset())

    def load_config(self):
        try:
            with open(CONFIG_FILE) as f:
                c = json.load(f)
                self.dark_mode = c.get("dark", True)
                self.colors = THEMES["dark" if self.dark_mode else "light"]
        except:
            pass

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.colors = THEMES["dark" if self.dark_mode else "light"]
        with open(CONFIG_FILE, "w") as f:
            json.dump({"dark": self.dark_mode}, f)
        self.build_ui()
        if self.current_index < len(self.image_list):
            self.request_image(self.current_index)

if __name__ == "__main__":
    root = Tk()
    app = TurboSorter(root)
    root.mainloop()
