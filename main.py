"""Keyboard-driven photo culling for Windows."""

import os
import json
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from tkinter import (
    Canvas, Frame, Label, Button, Text, TclError,
    filedialog, messagebox, ttk, Scale, HORIZONTAL, Toplevel
)
import exifread
from PIL import Image, ImageTk, ImageOps, ImageEnhance, ExifTags
from tkinterdnd2 import COPY, DND_FILES, REFUSE_DROP, TkinterDnD

from sorting import load_progress, save_decision, undo_decision

# ───── Config ─────
APP_VERSION = "1.1.0"
CONFIG_FILE = "turbo_sorter_config.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".bmp"}
ACTIONS = {"keep": "Keep", "discard": "Discard", "maybe": "Maybe"}
THUMB_WIDTH = 120
FRAME_INTERVAL_MS = 16

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

            with Image.open(path) as source:
                if source.format == "JPEG":
                    width, height = source.size
                    if source.getexif().get(ExifTags.Base.Orientation, 1) in (5, 6, 7, 8):
                        width, height = height, width
                    scale = min(target_width / width, target_height / height, 1)
                    # Use the fitted size in the JPEG's stored orientation.
                    source.draft("RGB", (max(1, int(source.width * scale)),
                                         max(1, int(source.height * scale))))
                image = ImageOps.exif_transpose(source)
                if image.mode != "RGB":
                    image = image.convert("RGB")
            image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
            return image, exif_text

        except Exception as e:
            print(f"Loader Error: {e}")
            return None, str(e)

    @staticmethod
    def load_thumbnail(path, thumb_size=120):
        """Load a small thumbnail for the filmstrip."""
        try:
            with Image.open(path) as source:
                if source.format == "JPEG":
                    source.draft("RGB", (thumb_size, thumb_size))
                image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
            return image
        except (OSError, ValueError, Image.DecompressionBombError):
            return None


class TurboSorter:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Turbo Photo Sorter {APP_VERSION}")
        self.root.geometry("1600x1000")
        self.root.minsize(1200, 700)

        # State
        self.source_dir = None
        self.image_list = []
        self.current_index = 0
        self.history = []
        self.processed_files = set()
        self.remaining = 0

        self.preview_pool = ThreadPoolExecutor(max_workers=2)
        self.thumb_pool = ThreadPoolExecutor(max_workers=2)
        self.save_pool = ThreadPoolExecutor(max_workers=1)
        self.preview_jobs = {}
        self.thumb_jobs = {}
        self.cache = {}
        self.thumb_cache = {}
        self.thumb_slots = {}
        self.save_job = None
        self.canvas_dim = (1200, 900)
        self.preview_dim = (root.winfo_screenwidth(), root.winfo_screenheight())

        # Display State
        self.base_image = None
        self.photo_ref = None
        self.render_job = None
        self.adjustment_key = None
        self.adjusted_preview = None
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
        self.fs_photo = None

        self.dark_mode = True
        self.colors = THEMES["dark"]

        self.load_config()
        self.build_ui()
        self.bind_drop_target(self.root)
        self.bind_keys()
        
        # Start queue listeners
        self.check_jobs()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

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

        self.placeholder = Label(self.canvas, text="📁  Drop photos or a folder here\n\nClick here or press Ctrl+O",
                                 font=("Segoe UI", 20), bg=self.colors["bg"], fg=self.colors["text_dim"],
                                 justify="center")
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        self.placeholder.bind("<Button-1>", lambda event: self.load_source())

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
        self.scale_bright.set(self.brightness_val)
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
        self.scale_contrast.set(self.contrast_val)
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

        navigation = Frame(btn_frame, bg=self.colors["panel"])
        navigation.pack(fill="x", pady=(4, 0))
        for label, offset in (("Previous  [", -1), ("Next  ]", 1)):
            Button(navigation, text=label, command=lambda step=offset: self.browse(step),
                   bg=self.colors["bg"], fg=self.colors["fg"], relief="flat",
                   cursor="hand2").pack(side="left", fill="x", expand=True, padx=2)

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
                                     height=108)
        self.filmstrip_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 2))
        self.filmstrip_frame.grid_propagate(False)

        # Filmstrip canvas for scrolling
        self.filmstrip_canvas = Canvas(self.filmstrip_frame, bg=self.colors["filmstrip_bg"], 
                                       highlightthickness=0, height=90)
        self.thumb_slots.clear()
        scrollbar = ttk.Scrollbar(self.filmstrip_frame, orient="horizontal",
                                  command=self.scroll_filmstrip)
        scrollbar.pack(side="bottom", fill="x")
        self.filmstrip_canvas.pack(fill="both", expand=True)
        self.filmstrip_canvas.configure(xscrollcommand=scrollbar.set)
        self.filmstrip_canvas.bind("<Configure>", self.draw_filmstrip)
        self.filmstrip_canvas.bind("<Button-1>", self.select_thumbnail)

        # --- 4. Status Bar ---
        self.status_bar = Frame(self.root, bg=self.colors["panel"], height=24,
                                highlightbackground=self.colors["border"], highlightthickness=1)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 5))
        self.status_bar.grid_propagate(False)

        self.status_label = Label(self.status_bar, text="Ready — Drop photos or open a folder with Ctrl+O",
                                  bg=self.colors["panel"], fg=self.colors["text_dim"],
                                  font=("Segoe UI", 9), anchor="w", padx=10)
        self.status_label.pack(side="left", fill="x", expand=True)

        self.filename_label = Label(self.status_bar, text="", bg=self.colors["panel"], 
                                    fg=self.colors["text_dim"], font=("Segoe UI", 9), anchor="e", padx=10)
        self.filename_label.pack(side="right")

        # Setup interactions
        self.setup_interactions()
        self.bind_drop_target(self.canvas)
        self.bind_drop_target(self.placeholder)

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
        if self.is_dragging:
            self.is_dragging = False
            self.refresh_image_visuals()
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
        if self.base_image is not None:
            self.refresh_image_visuals()
        elif self.source_dir is not None and self.current_index >= len(self.image_list):
            self.show_finished()

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


    def render_preview(self, canvas, width, height, pan_x=0, pan_y=0):
        canvas.delete("img_tag")
        if self.base_image is None:
            return None
        key = (self.base_image, self.brightness_val, self.contrast_val)
        if self.adjustment_key is None or (
            key[0] is not self.adjustment_key[0] or key[1:] != self.adjustment_key[1:]
        ):
            image = self.base_image
            if self.brightness_val != 1:
                image = ImageEnhance.Brightness(image).enhance(self.brightness_val)
            if self.contrast_val != 1:
                image = ImageEnhance.Contrast(image).enhance(self.contrast_val)
            self.adjustment_key, self.adjusted_preview = key, image
        image = self.adjusted_preview
        scale = min(width / image.width, height / image.height) * 0.99 * self.zoom_level
        scaled_width = max(1, int(image.width * scale))
        scaled_height = max(1, int(image.height * scale))
        origin_x = (width - scaled_width) // 2 + pan_x
        origin_y = (height - scaled_height) // 2 + pan_y
        left, top = max(0, origin_x), max(0, origin_y)
        right = min(width, origin_x + scaled_width)
        bottom = min(height, origin_y + scaled_height)
        if left >= right or top >= bottom:
            return None
        # Render only pixels inside the viewport, even at high zoom.
        x_ratio, y_ratio = image.width / scaled_width, image.height / scaled_height
        box = ((left - origin_x) * x_ratio, (top - origin_y) * y_ratio,
               min(image.width, (right - origin_x) * x_ratio),
               min(image.height, (bottom - origin_y) * y_ratio))
        sampling = Image.Resampling.BILINEAR if self.is_dragging else Image.Resampling.LANCZOS
        image = image.resize((right - left, bottom - top), sampling, box=box)
        photo = ImageTk.PhotoImage(image)
        canvas.create_image(left, top, anchor="nw", image=photo, tags="img_tag")
        canvas.tag_lower("img_tag")
        return photo

    def refresh_image_visuals(self):
        if self.render_job is None:
            self.render_job = self.root.after(FRAME_INTERVAL_MS, self.render_frame)

    def render_frame(self):
        self.render_job = None
        if self.is_fullscreen:
            self.update_fullscreen_image()
        else:
            self.photo_ref = self.render_preview(self.canvas, *self.canvas_dim, self.pan_x, self.pan_y)

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
        
        self.fs_canvas.bind("<Configure>", lambda event: self.refresh_image_visuals())
        self.fullscreen_window.protocol("WM_DELETE_WINDOW", self.exit_fullscreen)
        self.fullscreen_window.bind("<Escape>", lambda event: self.exit_fullscreen())
        self.fullscreen_window.bind("<MouseWheel>", self.on_fs_mousewheel)
        self.bind_keys(self.fullscreen_window)
        self.fs_canvas.focus_set()
        self.refresh_image_visuals()
        canvas = self.fs_canvas
        self.root.after_idle(lambda: self.show_fullscreen_hints() if self.fs_canvas is canvas else None)

    def update_fullscreen_image(self):
        if not self.is_fullscreen:
            return
        width = self.fs_canvas.winfo_width()
        height = self.fs_canvas.winfo_height()
        self.fs_photo = self.render_preview(self.fs_canvas, width, height)
        self.fs_canvas.delete("caption")
        if self.current_index < len(self.image_list):
            filename = self.image_list[self.current_index]
            if self.base_image is None:
                filename = ("Loading…  " if self.current_index not in self.cache
                            else "Preview unavailable  ") + filename
        else:
            filename = "All photos reviewed"
        self.fs_canvas.create_text(width // 2, height - 24, text=filename,
                                   fill=self.colors["text_dim"], font=("Segoe UI", 12),
                                   tags="caption")

    def show_fullscreen_hints(self):
        """Show temporary overlay hints in fullscreen."""
        if not self.fullscreen_window:
            return
        
        fw = self.fs_canvas.winfo_width()
        fh = self.fs_canvas.winfo_height()
        
        hints = [
            "→ / K: Keep    ↓ / N: Discard    M: Maybe    Ctrl+Z: Undo    Esc: Exit",
            " [ / ]: Browse    Mouse wheel: Zoom"
        ]
        
        for i, hint in enumerate(hints):
            self.fs_canvas.create_text(
                fw // 2, 30 + i * 25,
                text=hint, fill=self.colors["text_dim"],
                font=("Segoe UI", 11), tags="hints"
            )
        
        # Remove hints after 3 seconds
        canvas = self.fs_canvas
        self.root.after(3000, lambda: canvas.delete("hints") if self.fs_canvas is canvas else None)

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
            self.fs_photo = None
        self.refresh_image_visuals()

    # ───── LOADING ENGINE ─────
    def bind_drop_target(self, widget):
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind("<<DropEnter>>", lambda event: COPY)
        widget.dnd_bind("<<Drop:DND_Files>>", self.on_drop)

    def on_drop(self, event):
        if self.save_job is not None:
            self.update_status("Wait for the current decision to finish saving")
            return REFUSE_DROP
        try:
            paths = self.root.tk.splitlist(event.data)
        except TclError:
            return REFUSE_DROP
        self.root.after_idle(self.open_dropped_paths, paths)
        return COPY

    def open_dropped_paths(self, paths):
        entries = list(dict.fromkeys(Path(path) for path in paths))
        try:
            is_folder = len(entries) == 1 and entries[0].is_dir()
            are_photos = entries and all(entry.suffix.lower() in IMAGE_EXTENSIONS
                                         and entry.is_file() for entry in entries)
        except (OSError, ValueError) as error:
            self.show_error("Could not open dropped files", error)
            return
        if is_folder:
            self.load_source(entries[0])
            return
        if not are_photos:
            self.update_status("Drop a folder or supported photo files")
            return
        folder = entries[0].parent
        if any(entry.parent != folder for entry in entries):
            self.update_status("Drop photos from one folder at a time")
            return
        self.load_source(folder, selected_files=entries)

    def load_source(self, folder=None, *, selected_files=None):
        if self.save_job is not None:
            return
        if folder is None:
            folder = filedialog.askdirectory()
        if not folder:
            return

        folder = Path(folder)
        try:
            processed = load_progress(folder)
            entries = folder.iterdir() if selected_files is None else selected_files
            images = sorted((entry.name for entry in entries
                             if entry.suffix.lower() in IMAGE_EXTENSIONS
                             and entry.is_file() and entry.name not in processed),
                            key=str.casefold)
        except (OSError, ValueError) as error:
            messagebox.showerror("Could not open folder", str(error), parent=self.root)
            return

        for jobs in (self.preview_jobs, self.thumb_jobs):
            for future in jobs.values():
                future.cancel()
            jobs.clear()
        self.source_dir = folder
        self.image_list = images
        self.processed_files = processed
        self.remaining = len(images)
        self.history.clear()
        self.cache.clear()
        self.thumb_cache.clear()
        self.lbl_action.config(text="Ready", fg=self.colors["text_dim"])
        self.filmstrip_canvas.delete("all")
        self.thumb_slots.clear()
        self.filmstrip_canvas.configure(scrollregion=(0, 0, len(images) * THUMB_WIDTH, 80))
        self.filmstrip_canvas.xview_moveto(0)
        self.placeholder.place_forget()
        self.show_index(0)
        if images:
            self.update_status(f"Loaded {len(images)} photos from {folder.name}")
        elif selected_files is not None:
            self.update_status("The dropped photos have already been reviewed")
        else:
            self.update_status(f"No unreviewed photos in {folder.name}")

    def scroll_filmstrip(self, *args):
        self.filmstrip_canvas.xview(*args)
        self.draw_filmstrip()

    def select_thumbnail(self, event):
        index = int(self.filmstrip_canvas.canvasx(event.x) // THUMB_WIDTH)
        self.navigate_to(index)
        self.canvas.focus_set()

    def draw_filmstrip(self, event=None):
        canvas = self.filmstrip_canvas
        start = max(0, int(canvas.canvasx(0) // THUMB_WIDTH))
        end = min(len(self.image_list),
                  int(canvas.canvasx(canvas.winfo_width()) // THUMB_WIDTH) + 1)
        visible = range(start, end)
        for index in list(self.thumb_jobs):
            if index not in visible:
                self.thumb_jobs.pop(index).cancel()
        self.thumb_cache = {i: self.thumb_cache[i] for i in visible if i in self.thumb_cache}
        for index in self.thumb_slots.keys() - visible:
            canvas.delete(f"thumb{index}")
            del self.thumb_slots[index]
        for index in visible:
            if index not in self.thumb_cache and index not in self.thumb_jobs:
                path = self.source_dir / self.image_list[index]
                self.thumb_jobs[index] = self.thumb_pool.submit(ImageLoader.load_thumbnail, path, 64)
            image = self.thumb_cache.get(index)
            reviewed = self.image_list[index] in self.processed_files
            selected = index == self.current_index
            previous = self.thumb_slots.get(index)
            if previous is not None and image is previous[0] and (reviewed, selected) == previous[1]:
                continue
            x = index * THUMB_WIDTH + THUMB_WIDTH // 2
            tag = f"thumb{index}"
            canvas.delete(tag)
            border = self.colors["highlight" if selected else "border"]
            canvas.create_rectangle(x - 55, 3, x + 55, 80, outline=border, tags=tag)
            photo = None
            if image is not None:
                photo = ImageTk.PhotoImage(image)
                canvas.create_image(x, 34, image=photo, tags=tag)
            canvas.create_text(x, 72, text=f"{index + 1}" + ("  ✓" if reviewed else ""),
                               fill=self.colors["keep" if reviewed else "text_dim"],
                               font=("Segoe UI", 8), tags=tag)
            self.thumb_slots[index] = (image, (reviewed, selected), photo)

    def browse(self, step):
        self.navigate_to(self.current_index + step)

    def navigate_to(self, index):
        if self.save_job is None and index != self.current_index and 0 <= index < len(self.image_list):
            self.show_index(index)

    def show_index(self, index):
        self.current_index = index
        self.base_image = None
        self.adjustment_key = None
        self.adjusted_preview = None
        self.photo_ref = None
        self.is_dragging = False
        self.canvas.configure(cursor="crosshair")
        self.zoom_level = 1.0
        self.pan_x = self.pan_y = 0
        self.reset_adjustments()
        self.canvas.delete("all")
        self.loading_label.place_forget()
        self.exif_box.config(state="normal")
        self.exif_box.delete("1.0", "end")
        self.exif_box.config(state="disabled")
        self.update_ui_text()

        if index < len(self.image_list):
            filename = self.image_list[index]
            self.filename_label.config(text=filename)
            self.update_status(f"Photo {index + 1} of {len(self.image_list)}")
            width = self.filmstrip_canvas.winfo_width()
            left = self.filmstrip_canvas.canvasx(0)
            if index * THUMB_WIDTH < left or (index + 1) * THUMB_WIDTH > left + width:
                offset = max(0, (index + 0.5) * THUMB_WIDTH - width / 2)
                self.filmstrip_canvas.xview_moveto(offset / (len(self.image_list) * THUMB_WIDTH))
            self.request_image(index)
        else:
            self.filename_label.config(text="")
            self.show_finished()
        self.draw_filmstrip()
        if self.is_fullscreen:
            self.fs_canvas.delete("img_tag")
            self.fs_photo = None
            self.refresh_image_visuals()

    def request_image(self, index):
        nearby = [i for i in (index, index + 1, index - 1, index + 2)
                  if 0 <= i < len(self.image_list)]
        for i in list(self.preview_jobs):
            if i not in nearby:
                self.preview_jobs.pop(i).cancel()
        self.cache = {i: self.cache[i] for i in nearby if i in self.cache}
        for i in nearby:
            if i not in self.cache and i not in self.preview_jobs:
                path = self.source_dir / self.image_list[i]
                self.preview_jobs[i] = self.preview_pool.submit(
                    ImageLoader.load_and_process, path, *self.preview_dim
                )
        if index in self.cache:
            self.display_preview(index)
        else:
            self.loading_label.config(text="Loading preview…")
            self.loading_label.place(relx=0.5, rely=0.5, anchor="center")

    def check_jobs(self):
        for index, future in list(self.preview_jobs.items()):
            if future.done():
                del self.preview_jobs[index]
                self.cache[index] = future.result()
                if index == self.current_index:
                    self.display_preview(index)

        changed = False
        for index, future in list(self.thumb_jobs.items()):
            if future.done():
                del self.thumb_jobs[index]
                self.thumb_cache[index] = future.result()
                changed = True
        if changed:
            self.draw_filmstrip()

        if self.save_job is not None and self.save_job[0].done():
            self.finish_sort()
        self.root.after(FRAME_INTERVAL_MS, self.check_jobs)

    def display_preview(self, index):
        image, metadata = self.cache[index]
        self.base_image = image
        if image is None:
            self.loading_label.config(text="Preview unavailable")
            self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.loading_label.place_forget()
        self.exif_box.config(state="normal")
        self.exif_box.delete("1.0", "end")
        self.exif_box.insert("end", self.image_list[index] + "\n" + metadata)
        self.exif_box.config(state="disabled")
        self.refresh_image_visuals()

    # ───── SORTING LOGIC ─────
    def sort(self, action):
        if self.save_job is not None or self.current_index >= len(self.image_list):
            return
        filename = self.image_list[self.current_index]
        if filename in self.processed_files:
            self.update_status("Already reviewed. Use Ctrl+Z to undo your latest decision.")
            return
        if self.base_image is None and self.current_index not in self.cache:
            self.update_status("Wait for the current preview before sorting")
            return
        adjusted = None
        if self.base_image is not None and (self.brightness_val != 1 or self.contrast_val != 1):
            adjusted = partial(self.save_adjusted_image,
                               brightness=self.brightness_val, contrast=self.contrast_val)
        future = self.save_pool.submit(save_decision, self.source_dir, filename, ACTIONS[action],
                                       self.processed_files.copy(), adjusted)
        self.save_job = (future, self.current_index, action)
        self.update_status(f"Saving {filename}…")

    @staticmethod
    def save_adjusted_image(source, output, brightness, contrast):
        with Image.open(source) as original:
            image_format = original.format
            image = ImageOps.exif_transpose(original)
            image = image.convert("RGBA" if "A" in image.getbands() or "transparency" in image.info
                                  else "RGB")
        if brightness != 1:
            image = ImageEnhance.Brightness(image).enhance(brightness)
        if contrast != 1:
            image = ImageEnhance.Contrast(image).enhance(contrast)
        image.save(output, format=image_format, quality=95)

    def finish_sort(self):
        future, index, action = self.save_job
        self.save_job = None
        filename = self.image_list[index]
        try:
            outputs = future.result()
        except Exception as error:
            self.show_error("Could not save decision", error)
            return

        self.processed_files.add(filename)
        self.remaining -= 1
        self.history.append((index, outputs))
        next_index = len(self.image_list)
        if self.remaining:
            for offset in range(1, len(self.image_list)):
                candidate = (index + offset) % len(self.image_list)
                if self.image_list[candidate] not in self.processed_files:
                    next_index = candidate
                    break
        self.show_index(next_index)
        color = self.colors[action]
        self.lbl_action.config(text=action.upper(), fg=color)
        if self.remaining:
            self.flash_overlay(action.upper(), color)
        self.update_status(f"{ACTIONS[action]} → {filename}" if self.remaining
                           else f"All {len(self.image_list)} photos reviewed")

    def undo(self):
        if self.save_job is not None or not self.history:
            return
        index, outputs = self.history[-1]
        filename = self.image_list[index]
        try:
            cleanup = undo_decision(self.source_dir, filename, outputs, self.processed_files)
        except OSError as error:
            self.show_error("Could not undo decision", error)
            return

        self.history.pop()
        self.processed_files.remove(filename)
        self.remaining += 1
        self.show_index(index)
        self.lbl_action.config(text="UNDO", fg=self.colors["highlight"])
        if cleanup:
            self.show_error("Undid decision, but could not remove temporary copies", cleanup)
        else:
            self.update_status(f"Undid decision for {filename}")

    def show_error(self, title, error):
        self.update_status(title)
        parent = self.fullscreen_window if self.is_fullscreen else self.root
        messagebox.showerror(title, str(error), parent=parent)

    def close(self):
        if self.save_job is not None:
            self.show_error("Save in progress", "Wait for the current decision to finish saving.")
            return
        for pool in (self.preview_pool, self.thumb_pool, self.save_pool):
            pool.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()

    def flash_overlay(self, text, color):
        w = self.canvas.winfo_width()
        tag = self.canvas.create_text(w//2, 100, text=text, fill=color, 
                                      font=("Segoe UI", 60, "bold"))
        canvas = self.canvas
        canvas.after(400, lambda: canvas.delete(tag) if canvas.winfo_exists() else None)

    def update_ui_text(self):
        reviewed = len(self.image_list) - self.remaining
        self.progress_text.config(text=f"{reviewed} / {len(self.image_list)}")
        self.progress_bar.configure(maximum=max(1, len(self.image_list)), value=reviewed)

    def update_status(self, message):
        """Update the status bar message."""
        self.status_label.config(text=message)

    def show_finished(self):
        self.canvas.delete("completion")
        self.canvas.create_text(
            self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2,
            text="All photos reviewed" if self.image_list else "No unreviewed photos",
            font=("Segoe UI", 28, "bold"), fill=self.colors["keep"], tags="completion"
        )

    def bind_keys(self, window=None):
        if window is None:
            window = self.root
        shortcuts = {
            "<Right>": lambda: self.sort("keep"), "<k>": lambda: self.sort("keep"),
            "<K>": lambda: self.sort("keep"), "<space>": lambda: self.sort("keep"),
            "<Down>": lambda: self.sort("discard"), "<n>": lambda: self.sort("discard"),
            "<N>": lambda: self.sort("discard"),
            "<m>": lambda: self.sort("maybe"), "<M>": lambda: self.sort("maybe"),
            "<bracketleft>": lambda: self.browse(-1), "<bracketright>": lambda: self.browse(1),
            "<Control-z>": self.undo, "<F11>": self.toggle_fullscreen,
            "<plus>": self.zoom_in, "<equal>": self.zoom_in, "<minus>": self.zoom_out,
            "<Key-0>": self.zoom_reset,
        }
        if window is self.root:
            shortcuts["<Control-o>"] = self.load_source

        def handle(event, command):
            if event.keysym == "space" and isinstance(event.widget, Button):
                return None
            if event.keysym in ("Left", "Right", "Up", "Down") and isinstance(event.widget, Scale):
                return None
            command()
            return "break"

        for key, command in shortcuts.items():
            window.bind(key, lambda event, callback=command: handle(event, callback))

    def load_config(self):
        try:
            with open(CONFIG_FILE) as f:
                c = json.load(f)
                self.dark_mode = c.get("dark", True)
                self.colors = THEMES["dark" if self.dark_mode else "light"]
        except:
            pass

    def toggle_theme(self):
        if self.is_fullscreen:
            self.exit_fullscreen()
        self.dark_mode = not self.dark_mode
        self.colors = THEMES["dark" if self.dark_mode else "light"]
        with open(CONFIG_FILE, "w") as f:
            json.dump({"dark": self.dark_mode}, f)
        status = self.status_label.cget("text")
        action = self.lbl_action.cget("text")
        for widget in self.root.winfo_children():
            widget.destroy()
        self.build_ui()
        self.update_ui_text()
        self.lbl_action.config(text=action)
        if self.source_dir is not None:
            self.placeholder.place_forget()
            self.filmstrip_canvas.configure(scrollregion=(0, 0, len(self.image_list) * THUMB_WIDTH, 80))
            if self.current_index < len(self.image_list):
                self.filename_label.config(text=self.image_list[self.current_index])
                self.filmstrip_canvas.xview_moveto(max(0, self.current_index - 2) / len(self.image_list))
                self.request_image(self.current_index)
            else:
                self.show_finished()
        self.update_status(status)

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = TurboSorter(root)
    root.mainloop()
