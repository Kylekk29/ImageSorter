import os
import shutil


class FileSorter:
    SORT_FOLDERS = ["Keep", "Discard", "Maybe"]
    MODIFIED_SUFFIXES = ["Keep_Modified", "Discard_Modified", "Maybe_Modified"]

    def __init__(self, base_folder):
        self.base_folder = base_folder

    def ensure_folders(self):
        for folder in self.SORT_FOLDERS + self.MODIFIED_SUFFIXES:
            path = os.path.join(self.base_folder, folder)
            os.makedirs(path, exist_ok=True)

    def sort_file(self, file_path, action, file_name=None):
        if file_name is None:
            file_name = os.path.basename(file_path)

        folder_map = {"keep": "Keep", "discard": "Discard", "maybe": "Maybe"}
        folder = folder_map.get(action)
        if not folder:
            return None

        dest = os.path.join(self.base_folder, folder, file_name)
        try:
            shutil.copy2(file_path, dest)
            return dest
        except (shutil.Error, IOError) as e:
            return None

    def save_modified(self, pil_image, action, file_name, quality=95):
        folder_map_mod = {
            "keep": "Keep_Modified",
            "discard": "Discard_Modified",
            "maybe": "Maybe_Modified",
        }
        folder = folder_map_mod.get(action)
        if not folder:
            return None

        os.makedirs(os.path.join(self.base_folder, folder), exist_ok=True)
        dest = os.path.join(self.base_folder, folder, file_name)
        try:
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
            pil_image.save(dest, "JPEG", quality=quality)
            return dest
        except IOError:
            return None

    @staticmethod
    def ensure_dir(path):
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def get_image_files(folder):
        exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
        files = []
        for f in os.listdir(folder):
            ext = os.path.splitext(f)[1].lower()
            if ext in exts:
                files.append(os.path.join(folder, f))
        return sorted(files)

    @staticmethod
    def generate_stats(history, folder_path):
        lines = []
        lines.append("=" * 50)
        lines.append("TURBO PHOTO SORTER - STATISTICS")
        lines.append("=" * 50)
        from datetime import datetime
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Location: {folder_path}")
        lines.append("")

        kept = [h for h in history if h.get("action") == "keep"]
        discarded = [h for h in history if h.get("action") == "discard"]
        maybe = [h for h in history if h.get("action") == "maybe"]

        lines.append(f"Total processed: {len(history)}")
        lines.append(f"  Kept:     {len(kept)}")
        lines.append(f"  Discarded: {len(discarded)}")
        lines.append(f"  Maybe:    {len(maybe)}")
        lines.append("")

        if kept:
            lines.append("--- Kept Files ---")
            for h in kept:
                lines.append(f"  {h.get('file', '?')}")
        if discarded:
            lines.append("--- Discarded Files ---")
            for h in discarded:
                lines.append(f"  {h.get('file', '?')}")
        if maybe:
            lines.append("--- Maybe Files ---")
            for h in maybe:
                lines.append(f"  {h.get('file', '?')}")

        return "\n".join(lines)
