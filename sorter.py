# ===============================================
# TURBO PHOTO SORTER v4.3 — Exifread Integration
# Uses 'exifread' for robust metadata.
# Fixes all EXIF orientation bugs.
# Requirements: pip install pillow exifread
# ===============================================

import os
import json
import shutil
import threading
from tkinter import (
    Tk, Canvas, Frame, Label, Button, Text,
    filedialog, messagebox, ttk
)
import exifread  # <-- ADDED: For robust EXIF reading
from PIL import Image, ImageTk, ExifTags, ImageOps  # <-- ADDED: ImageOps

# ───── Config ─────
CONFIG_FILE = "turbo_sorter_config.json"
LOG_FILE_NAME = "turbo_sorter_log.json"

THEMES = {
    "dark": {
        "bg": "#1e1e1e", "fg": "#ffffff", "panel": "#2d2d2d",
        "keep": "#4caf50", "discard": "#f44336", "maybe": "#ff9800",
        "highlight": "#2196f3", "text_dim": "#aaaaaa",
        "exif_bg": "#0d0d0d", "exif_fg": "#dddddd",
        "btn_fg": "#ffffff",
    },
    "light": {
        "bg": "#f5f5f5", "fg": "#000000", "panel": "#ffffff",
        "keep": "#388e3c", "discard": "#d32f2f", "maybe": "#f57c00",
        "highlight": "#1976d2", "text_dim": "#555555",
        "exif_bg": "#f8f8f8", "exif_fg": "#000000",
        "btn_fg": "#ffffff",
    }
}

class TurboSorter:
    def __init__(self, root):
        self.root = root
        self.root.title("Turbo Photo Sorter v4.3 — Exifread Edition")
        self.root.geometry("1600x1000")
        self.root.minsize(1000, 600)

        # State
        self.source_dir = ""
        self.keep_dir = self.discard_dir = self.maybe_dir = ""
        self.image_list = []
        self.total_images_in_folder = 0
        self.current_index = 0
        self.history = []
        self.processed_log_file = ""
        self.processed_files = set()
        self.dark_mode = True
        self.colors = THEMES["dark"]
        self.photo = None
        self.current_pil = None

        self.load_config()
        self.build_ui()
        self.bind_keys()

    def build_ui(self):
        # (This method is unchanged from v4.2)
        self.root.configure(bg=self.colors["bg"])
        self.root.grid_columnconfigure(0, weight=5)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.canvas = Canvas(self.root, bg=self.colors["bg"], highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.canvas.bind("<Button-1>", lambda e: self.load_source())

        self.placeholder = Label(self.canvas, text="Click to Load Folder",
                                 font=("Segoe UI", 24), bg=self.colors["bg"], fg="#888888")
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        self.sidebar = Frame(self.root, bg=self.colors["panel"])
        self.sidebar.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        self.pad = Frame(self.sidebar, bg=self.colors["panel"])
        self.pad.pack(fill="both", expand=True, padx=22, pady=25)

        self.theme_button = Button(self.pad, text="Light Mode",
                                   command=self.toggle_theme,
                                   bg="#444", fg="#fff", relief="flat")
        self.theme_button.pack(anchor="e", pady=(0, 20))

        self.progress_text = Label(self.pad, text="Session: 0 / 0", font=("Segoe UI", 16, "bold"),
                                   bg=self.colors["panel"], fg=self.colors["fg"])
        self.progress_text.pack(anchor="w", pady=(0, 0))

        self.total_progress_text = Label(self.pad, text="Total: 0 / 0", font=("Segoe UI", 10),
                                   bg=self.colors["panel"], fg=self.colors["text_dim"])
        self.total_progress_text.pack(anchor="w", pady=(0, 10))

        self.progress_bar = ttk.Progressbar(self.pad, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 25))

        self.last_action_frame = ttk.LabelFrame(self.pad, text=" Last Action ")
        self.last_action_frame.pack(fill="x", pady=(0, 10))
        self.last_action = Label(self.last_action_frame, text="Ready", anchor="w",
                                 bg=self.colors["panel"], fg=self.colors["fg"],
                                 font=("Segoe UI", 11, "bold"), padx=10, pady=8)
        self.last_action.pack(fill="x")

        self.actions_frame = ttk.LabelFrame(self.pad, text=" Actions ")
        self.actions_frame.pack(fill="x", pady=(20, 10))
        self.btn_keep = self.btn("KEEP (Right / K / Space)", lambda: self.sort("keep"), self.colors["keep"], self.actions_frame)
        self.btn_discard = self.btn("DISCARD (Down / N)", lambda: self.sort("discard"), self.colors["discard"], self.actions_frame)
        self.btn_maybe = self.btn("MAYBE (M)", lambda: self.sort("maybe"), self.colors["maybe"], self.actions_frame)
        self.btn_undo = self.btn("⟲ UNDO (Ctrl+Z)", self.undo, "#666666", self.actions_frame)

        self.info_frame = ttk.LabelFrame(self.pad, text=" Image Info ")
        self.info_frame.pack(fill="both", expand=True, pady=(30, 0))
        self.exif_box = Text(self.info_frame, height=10, font=("Consolas", 10),
                             bg=self.colors["exif_bg"], fg=self.colors["exif_fg"],
                             relief="flat", padx=10, pady=10, borderwidth=0)
        self.exif_box.pack(fill="both", expand=True, padx=2, pady=(5,2))

    def btn(self, text, cmd, color, parent):
        # (This method is unchanged from v4.2)
        b = Button(parent, text=text, command=cmd, bg=color, fg=self.colors["btn_fg"],
                   font=("Segoe UI", 11, "bold"), relief="flat", pady=10,
                   activebackground=color, activeforeground=self.colors["btn_fg"])
        b.pack(fill="x", padx=8, pady=5)
        return b

    def toggle_theme(self):
        # (This method is unchanged from v4.2)
        self.dark_mode = not self.dark_mode
        self.colors = THEMES["dark" if self.dark_mode else "light"]
        self.recolor()
        self.save_config()

    def recolor(self):
        # (This method is unchanged from v4.2)
        self.theme_button.config(
            text="Dark Mode" if not self.dark_mode else "Light Mode",
            bg="#ddd" if self.dark_mode else "#444",
            fg="#000" if self.dark_mode else "#fff"
        )
        self.root.configure(bg=self.colors["bg"])
        self.canvas.configure(bg=self.colors["bg"])
        self.placeholder.configure(bg=self.colors["bg"], fg=self.colors["text_dim"])
        self.sidebar.configure(bg=self.colors["panel"])
        self.pad.configure(bg=self.colors["panel"])
        self.progress_text.configure(bg=self.colors["panel"], fg=self.colors["fg"])
        self.total_progress_text.configure(bg=self.colors["panel"], fg=self.colors["text_dim"])
        
        style = ttk.Style()
        style.configure("TLabelFrame", background=self.colors["panel"], borderwidth=1, relief="groove")
        style.configure("TLabelFrame.Label", background=self.colors["panel"], foreground=self.colors["text_dim"])
        self.last_action_frame.configure(style="TLabelFrame")
        self.actions_frame.configure(style="TLabelFrame")
        self.info_frame.configure(style="TLabelFrame")
        
        self.last_action.configure(bg=self.colors["panel"], fg=self.colors["fg"])
        self.btn_keep.configure(bg=self.colors["keep"], fg=self.colors["btn_fg"], activebackground=self.colors["keep"])
        self.btn_discard.configure(bg=self.colors["discard"], fg=self.colors["btn_fg"], activebackground=self.colors["discard"])
        self.btn_maybe.configure(bg=self.colors["maybe"], fg=self.colors["btn_fg"], activebackground=self.colors["maybe"])
        self.exif_box.configure(bg=self.colors["exif_bg"], fg=self.colors["exif_fg"])

    def bind_keys(self):
        # (This method is unchanged from v4.2)
        self.root.bind("<Right>", lambda e: self.sort("keep"))
        self.root.bind("<k>", lambda e: self.sort("keep"))
        self.root.bind("<space>", lambda e: self.sort("keep"))
        self.root.bind("<Down>", lambda e: self.sort("discard"))
        self.root.bind("<n>", lambda e: self.sort("discard"))
        self.root.bind("<m>", lambda e: self.sort("maybe"))
        self.root.bind("<Control-z>", lambda e: self.undo())

    def load_source(self):
        # (This method is unchanged from v4.2)
        folder = filedialog.askdirectory(title="Select Folder with Photos")
        if not folder:
            return

        self.source_dir = folder
        self.keep_dir = os.path.join(folder, "Keep")
        self.discard_dir = os.path.join(folder, "Discard")
        self.maybe_dir = os.path.join(folder, "Maybe")

        for d in (self.keep_dir, self.discard_dir, self.maybe_dir):
            os.makedirs(d, exist_ok=True)

        self.processed_log_file = os.path.join(self.source_dir, LOG_FILE_NAME)
        self.processed_files = self.load_processed_log()

        exts = (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".bmp")
        
        try:
            all_files_in_folder = sorted([
                f for f in os.listdir(folder)
                if f.lower().endswith(exts) and os.path.isfile(os.path.join(folder, f))
            ], key=lambda x: x.lower())
        except Exception as e:
            messagebox.showerror("Error", f"Could not read folder: {e}")
            return

        self.total_images_in_folder = len(all_files_in_folder)
        self.image_list = [f for f in all_files_in_folder if f not in self.processed_files]

        if not self.image_list:
            if self.total_images_in_folder > 0:
                messagebox.showinfo("All Done", "All photos in this folder have already been sorted.")
            else:
                messagebox.showinfo("No photos", "No supported images found in this folder.")
            return

        self.current_index = 0
        self.history.clear()
        self.placeholder.place_forget()
        self.update_progress()
        self.show_current()

    def show_current(self):
        if self.current_index >= len(self.image_list):
            self.canvas.delete("all")
            Label(self.canvas, text="SESSION COMPLETE!", font=("Segoe UI", 48, "bold"),
                  bg=self.colors["bg"], fg=self.colors["keep"]).place(relx=0.5, rely=0.5, anchor="center")
            self.current_pil = None
            return

        path = os.path.join(self.source_dir, self.image_list[self.current_index])
        try:
            img = Image.open(path)
            
            # --- MODIFIED: Use new, better orientation method ---
            img = self.apply_exif_orientation(img)
            
            self.current_pil = img.convert("RGB")
            self.display_current()
            
            # --- MODIFIED: Pass path to new exifread function ---
            self.show_exif(path) 
            
        except Exception as e:
            print(f"Error loading {path}: {e}")
            self.sort("discard")

    # --- ⬇︎ MODIFIED / UPGRADED METHOD ⬇︎ ---
    def apply_exif_orientation(self, img):
        """
        Uses ImageOps.exif_transpose to auto-rotate based on EXIF.
        This is far more robust than the old manual method and
        handles all 8 orientation types correctly.
        """
        try:
            img = ImageOps.exif_transpose(img)
        except Exception as e:
            print(f"Failed to apply EXIF orientation: {e}")
            pass  # Fail silently if EXIF data is bad
        return img

    def display_current(self):
        # (This method is unchanged from v4.2)
        if not self.current_pil:
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            self.root.after(50, self.display_current)
            return

        img = self.current_pil
        ratio = min(cw / img.width, ch / img.height) * 0.98
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)

        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, image=self.photo, anchor="center")

    def sort(self, action):
        # (This method is unchanged from v4.2)
        if self.current_index >= len(self.image_list):
            return

        filename = self.image_list[self.current_index]
        src = os.path.join(self.source_dir, filename)
        target_dir = {"keep": self.keep_dir, "discard": self.discard_dir, "maybe": self.maybe_dir}[action]
        dst = os.path.join(target_dir, filename)

        # ⬇︎ NEW CHECK HERE ⬇︎
        if not os.path.exists(src):
            messagebox.showwarning("File Missing", f"File '{filename}' not found at source. Removing from list.")
            # Remove the missing file from the list and re-index.
            del self.image_list[self.current_index]
            self.update_progress()
            self.root.after(50, self.show_current)
            return
        # ⬆︎ NEW CHECK HERE ⬆︎
        
        try:
            shutil.move(src, dst)
        # ... rest of your code ...
        except Exception as e:
            print(f"File move failed: {e}")
            messagebox.showerror("Move Error", f"Could not move file: {e}\nSkipping.")
            self.current_index += 1
            self.root.after(50, self.show_current)
            return

        self.history.append({"file": filename, "action": action, "src": src, "dst": dst})
        self.processed_files.add(filename)
        self.save_processed_log()

        self.last_action.config(text=f"{action.upper()}: {filename}", fg=self.colors[action])
        self.overlay(action.upper())

        self.current_index += 1
        self.update_progress()
        self.root.after(120, self.show_current)

    def undo(self):
        # (This method is unchanged from v4.2)
        if not self.history:
            return
        
        last = self.history.pop()
        filename = last["file"]
        src = last["dst"]
        dst = last["src"]

        try:
            shutil.move(src, dst)
        except Exception as e:
            print(f"Undo failed: {e}")
            messagebox.showerror("Undo Error", f"Could not move file back: {e}")
            self.history.append(last)
            return
        
        if filename in self.processed_files:
            self.processed_files.remove(filename)
            self.save_processed_log()

        self.current_index -= 1
        self.last_action.config(text="UNDO → " + filename, fg=self.colors["highlight"])
        self.update_progress()
        self.show_current()

    def overlay(self, text):
        # (This method is unchanged from v4.2)
        try:
            tag = self.canvas.create_text(
                self.canvas.winfo_width() // 2, 140,
                text=text,
                fill="white", font=("Segoe UI", 72, "bold"),
                tags="overlay"
            )
            self.root.after(700, lambda: self.canvas.delete(tag))
        except:
            pass

    # --- ⬇︎ MODIFIED / UPGRADED METHOD ⬇︎ ---
    def show_exif(self, path):
        """
        Uses the 'exifread' library to process the file
        for more robust metadata display.
        """
        self.exif_box.configure(state="normal")
        self.exif_box.delete(1.0, "end")
        name = os.path.basename(path)
        self.exif_box.insert("end", f"{name}\n{'─' * 60}\n")

        # Curated list of interesting tags
        interesting_tags = [
            'Image Make', 'Image Model', 'EXIF DateTimeOriginal',
            'EXIF FNumber', 'EXIF ExposureTime', 'EXIF ISOSpeedRatings',
            'EXIF FocalLength', 'EXIF LensModel', 'Image Software'
        ]

        try:
            # Open file in binary mode for exifread
            with open(path, 'rb') as f:
                tags = exifread.process_file(f, details=False)

            if not tags:
                self.exif_box.insert("end", "No EXIF data\n")
                self.exif_box.configure(state="disabled")
                return

            # Display the interesting tags
            for tag_name in interesting_tags:
                if tag_name in tags:
                    value = str(tags[tag_name])
                    # Clean up the tag name for display
                    display_name = tag_name.replace("Image ", "").replace("EXIF ", "")
                    self.exif_box.insert("end", f"{display_name:14}: {value}\n")

        except Exception as e:
            self.exif_box.insert("end", f"EXIF read failed: {e}\n")
        
        self.exif_box.configure(state="disabled") # Make read-only

    def update_progress(self):
        # (This method is unchanged from v4.2)
        session_total = len(self.image_list)
        session_done = self.current_index
        folder_total = self.total_images_in_folder
        
        self.progress_text.config(text=f"Session: {session_done} / {session_total}")
        self.progress_bar["maximum"] = session_total if session_total > 0 else 1
        self.progress_bar["value"] = session_done
        
        total_sorted_count = len(self.processed_files)
        self.total_progress_text.config(text=f"Total: {total_sorted_count} / {folder_total}")

    def save_processed_log(self):
        # (This method is unchanged from v4.2)
        try:
            with open(self.processed_log_file, "w") as f:
                json.dump({"processed_files": list(self.processed_files)}, f, indent=2)
        except Exception as e:
            print(f"Failed to save log: {e}")

    def load_processed_log(self):
        # (This method is unchanged from v4.2)
        if not os.path.exists(self.processed_log_file):
            return set()
        try:
            with open(self.processed_log_file) as f:
                data = json.load(f)
                return set(data.get("processed_files", []))
        except Exception as e:
            print(f"Failed to load log: {e}")
            return set()

    def save_config(self):
        # (This method is unchanged from v4.2)
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"dark": self.dark_mode}, f)
        except:
            pass

    def load_config(self):
        # (This method is unchanged from v4.2)
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                self.dark_mode = config.get("dark", True)
                self.colors = THEMES["dark" if self.dark_mode else "light"]
        except:
            pass

if __name__ == "__main__":
    root = Tk()
    app = TurboSorter(root)
    root.mainloop()
