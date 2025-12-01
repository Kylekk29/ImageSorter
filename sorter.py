import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ExifTags
import threading
import queue
import time

# --- Configuration ---
COLORS = {
    "bg": "#2b2b2b",          
    "fg": "#ffffff",          
    "panel": "#3c3f41",       
    "accent_keep": "#4caf50", 
    "accent_discard": "#f44336", 
    "highlight": "#2196f3",
    "text_dim": "#aaaaaa",
    "warning": "#ff9800"
}

FONTS = {
    "header": ("Segoe UI", 12, "bold"),
    "body": ("Segoe UI", 10),
    "mono": ("Consolas", 9),
    "overlay": ("Segoe UI", 24, "bold")
}

class FastThreadedSorter:
    def __init__(self, root):
        self.root = root
        self.root.title("Fast Image Sorter - Turbo Mode 🚀")
        self.root.geometry("1400x900")
        self.root.configure(bg=COLORS["bg"])

        # State
        self.image_list = []
        self.current_index = 0
        self.source_dir = ""
        self.keep_dir = ""
        self.discard_dir = ""
        self.history = [] 
        
        # --- THREADING SETUP ---
        # The queue holds the copy jobs
        self.copy_queue = queue.Queue()
        # Start the background worker
        self.stop_thread = False
        self.worker_thread = threading.Thread(target=self.background_worker, daemon=True)
        self.worker_thread.start()

        # Image Caching
        self.current_pil_image = None
        self.tk_image = None
        self.image_container_id = None

        self.setup_ui()
        self.bind_keys()
        
        # Start a UI updater loop to check queue status
        self.check_queue_status()

    def setup_ui(self):
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=1, minsize=380)
        self.root.rowconfigure(0, weight=1)

        # --- LEFT: Image ---
        self.image_frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.image_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.image_frame, bg=COLORS["bg"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.center_msg = tk.Label(self.image_frame, text="Open Source Folder", 
                                 bg=COLORS["bg"], fg="#666666", font=("Segoe UI", 18))
        self.center_msg.place(relx=0.5, rely=0.5, anchor="center")

        # --- RIGHT: Sidebar ---
        self.sidebar = tk.Frame(self.root, bg=COLORS["panel"])
        self.sidebar.grid(row=0, column=1, sticky="nsew")
        
        side_inner = tk.Frame(self.sidebar, bg=COLORS["panel"])
        side_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # 1. Progress & Queue Status
        self.lbl_progress = tk.Label(side_inner, text="0 / 0", bg=COLORS["panel"], fg=COLORS["fg"], font=("Segoe UI", 16, "bold"))
        self.lbl_progress.pack(anchor="e")
        
        self.progress_bar = ttk.Progressbar(side_inner, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(5, 5))

        # NEW: Pending Operations Indicator
        self.lbl_queue = tk.Label(side_inner, text="Ready", bg=COLORS["panel"], fg=COLORS["accent_keep"], font=("Segoe UI", 9))
        self.lbl_queue.pack(anchor="e", pady=(0, 15))

        # 2. Last Action
        self.action_frame = tk.LabelFrame(side_inner, text="Last Action", bg=COLORS["panel"], fg=COLORS["text_dim"], font=FONTS["body"])
        self.action_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.lbl_last_file = tk.Label(self.action_frame, text="...", anchor="w", bg=COLORS["panel"], fg=COLORS["fg"], font=("Segoe UI", 10, "bold"))
        self.lbl_last_file.pack(fill=tk.X, padx=5, pady=2)

        # 3. Controls
        ctrl_frame = tk.LabelFrame(side_inner, text="Setup", bg=COLORS["panel"], fg=COLORS["fg"], font=FONTS["header"])
        ctrl_frame.pack(fill=tk.X, pady=10)

        self.make_button(ctrl_frame, "📂 Load Source", self.select_source_folder, bg=COLORS["highlight"])
        self.make_button(ctrl_frame, "Target: Keep", self.select_keep_folder)
        self.make_button(ctrl_frame, "Target: Discard", self.select_discard_folder)

        # 4. Action Buttons
        act_frame = tk.LabelFrame(side_inner, text="Controls", bg=COLORS["panel"], fg=COLORS["fg"], font=FONTS["header"])
        act_frame.pack(fill=tk.X, pady=10)

        self.make_button(act_frame, "KEEP (Right)", lambda: self.process_image('keep'), bg=COLORS["accent_keep"])
        self.make_button(act_frame, "DISCARD (Down)", lambda: self.process_image('discard'), bg=COLORS["accent_discard"])
        self.make_button(act_frame, "⟲ Undo (Ctrl+Z)", self.undo_last, bg="#555555")

        # 5. EXIF
        tk.Label(side_inner, text="Image Data", bg=COLORS["panel"], fg=COLORS["text_dim"], font=FONTS["header"]).pack(anchor="w", pady=(10, 5))
        self.exif_text = tk.Text(side_inner, height=10, bg="#2b2b2b", fg="#dddddd", bd=0, font=FONTS["mono"], padx=8, pady=8)
        self.exif_text.pack(fill=tk.BOTH, expand=True)

    def make_button(self, parent, text, cmd, bg="#444444"):
        btn = tk.Button(parent, text=text, command=cmd, bg=bg, fg="white", 
                        relief="flat", font=("Segoe UI", 10), activebackground="#666666", activeforeground="white", pady=5)
        btn.pack(fill=tk.X, padx=5, pady=3)

    def bind_keys(self):
        self.root.bind('<k>', lambda e: self.process_image('keep'))
        self.root.bind('<Right>', lambda e: self.process_image('keep'))
        self.root.bind('<n>', lambda e: self.process_image('discard'))
        self.root.bind('<Down>', lambda e: self.process_image('discard'))
        self.root.bind('<Control-z>', self.undo_last)
        self.root.bind('<Configure>', self.on_resize)

    def on_resize(self, event):
        if event.widget == self.image_frame and self.current_pil_image:
            self.display_image(self.current_pil_image)

    # --- Background Worker ---
    def background_worker(self):
        """This runs in a separate thread forever"""
        while True:
            # Get task from queue
            task = self.copy_queue.get()
            if task is None: break
            
            src, dst = task
            try:
                # The heavy lifting happens here!
                shutil.copy2(src, dst)
            except Exception as e:
                print(f"Background copy error: {e}")
            
            self.copy_queue.task_done()

    def check_queue_status(self):
        """Updates the UI to show how many files are pending copy"""
        pending = self.copy_queue.qsize()
        if pending > 0:
            self.lbl_queue.config(text=f"⚠ Writing {pending} files...", fg=COLORS["warning"])
        else:
            self.lbl_queue.config(text="✔ All writes finished", fg=COLORS["accent_keep"])
        
        self.root.after(200, self.check_queue_status)

    # --- Logic ---
    def select_source_folder(self):
        folder = filedialog.askdirectory()
        if not folder: return
        self.source_dir = folder
        self.keep_dir = os.path.join(self.source_dir, "Keep")
        self.discard_dir = os.path.join(self.source_dir, "Discard")
        
        exts = ('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff')
        self.image_list = [f for f in os.listdir(folder) if f.lower().endswith(exts) and os.path.isfile(os.path.join(folder, f))]
        
        # Ensure targets exist immediately so we don't check every time
        if not os.path.exists(self.keep_dir): os.makedirs(self.keep_dir)
        if not os.path.exists(self.discard_dir): os.makedirs(self.discard_dir)

        if not self.image_list: return

        self.current_index = 0
        self.history.clear()
        self.center_msg.place_forget()
        self.update_status_ui()
        self.load_current_image()

    def select_keep_folder(self):
        f = filedialog.askdirectory(); 
        if f: self.keep_dir = f

    def select_discard_folder(self):
        f = filedialog.askdirectory(); 
        if f: self.discard_dir = f

    def load_current_image(self):
        if self.current_index >= len(self.image_list):
            self.canvas.delete("all")
            self.center_msg.config(text="All Done! 🎉")
            self.center_msg.place(relx=0.5, rely=0.5, anchor="center")
            return

        filename = self.image_list[self.current_index]
        path = os.path.join(self.source_dir, filename)

        try:
            self.current_pil_image = Image.open(path)
            self.display_image(self.current_pil_image)
            self.display_exif(self.current_pil_image, filename)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            self.current_index += 1
            self.load_current_image()

    def display_image(self, pil_img):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10: return

        img_w, img_h = pil_img.size
        ratio = min(w/img_w, h/img_h)
        new_size = (int(img_w * ratio), int(img_h * ratio))

        # Caching check
        if hasattr(self, '_cached_size') and self._cached_size == new_size and hasattr(self, '_cached_img_id') and self._cached_img_id == id(pil_img):
            pass 
        else:
            resized = pil_img.resize(new_size, Image.Resampling.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(resized)
            self._cached_size = new_size
            self._cached_img_id = id(pil_img)

        if self.image_container_id:
            self.canvas.itemconfig(self.image_container_id, image=self.tk_image)
            self.canvas.coords(self.image_container_id, w//2, h//2)
        else:
            self.image_container_id = self.canvas.create_image(w//2, h//2, anchor="center", image=self.tk_image)

    def display_exif(self, img, filename):
        self.exif_text.delete(1.0, tk.END)
        self.exif_text.insert(tk.END, f"FILE: {filename}\n{'='*25}\n")
        exif = img.getexif()
        if not exif:
            self.exif_text.insert(tk.END, "No EXIF.")
            return

        tags = {272:'Model', 306:'Date', 33434:'Exp', 33437:'F-Stop', 34855:'ISO'}
        for k, v in tags.items():
            if k in exif: self.exif_text.insert(tk.END, f"{v:8}: {exif[k]}\n")

    def process_image(self, action):
        if self.current_index >= len(self.image_list): return
        
        filename = self.image_list[self.current_index]
        src = os.path.join(self.source_dir, filename)
        target_dir = self.keep_dir if action == 'keep' else self.discard_dir
        dst = os.path.join(target_dir, filename)

        # 1. ADD TO QUEUE (Instant)
        self.copy_queue.put((src, dst))
        
        # 2. UPDATE HISTORY
        self.history.append({'src': src, 'dst': dst, 'index': self.current_index})

        # 3. UI FEEDBACK (Instant)
        self.show_overlay_feedback(action)
        self.lbl_last_file.config(text=f"✔ {filename}", fg=COLORS["accent_keep"] if action=='keep' else COLORS["accent_discard"])
        
        # 4. MOVE TO NEXT IMAGE (Instant)
        self.current_index += 1
        self.update_status_ui()
        self.load_current_image()

    def undo_last(self, event=None):
        if not self.history: return
        last = self.history.pop()
        
        # We try to delete the file if it exists. 
        # Note: If the background thread hasn't written it yet, this might fail harmlessly.
        if os.path.exists(last['dst']):
            try: os.remove(last['dst'])
            except: pass
        
        self.current_index = last['index']
        self.lbl_last_file.config(text="⟲ Undo Performed", fg=COLORS["highlight"])
        self.update_status_ui()
        self.load_current_image()

    def show_overlay_feedback(self, action):
        text = "KEPT" if action == 'keep' else "DISCARDED"
        color = COLORS["accent_keep"] if action == 'keep' else COLORS["accent_discard"]
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        
        text_tag = self.canvas.create_text(w//2, h//2, text=text, fill=color, font=FONTS["overlay"])
        self.root.after(300, lambda: self.canvas.delete(text_tag))

    def update_status_ui(self):
        total = len(self.image_list)
        self.lbl_progress.config(text=f"{self.current_index + 1} / {total}")
        self.progress_bar['maximum'] = total
        self.progress_bar['value'] = self.current_index

if __name__ == "__main__":
    root = tk.Tk()
    app = FastThreadedSorter(root)
    root.mainloop()