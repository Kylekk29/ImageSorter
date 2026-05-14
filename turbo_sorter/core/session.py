import json
import os
from datetime import datetime


class SessionLogger:
    def __init__(self, folder_path=""):
        self.folder_path = folder_path
        self.log_path = ""
        self._data = {"processed_files": [], "history": [], "timestamp": ""}
        if folder_path:
            self.set_folder(folder_path)

    def set_folder(self, folder_path):
        self.folder_path = folder_path
        self.log_path = os.path.join(folder_path, "turbo_sorter_log.json")
        self.load()

    def load(self):
        if self.log_path and os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {"processed_files": [], "history": [], "timestamp": ""}

    def save(self):
        if not self.log_path:
            return
        self._data["timestamp"] = datetime.now().isoformat()
        try:
            with open(self.log_path, "w") as f:
                json.dump(self._data, f, indent=2)
        except IOError:
            pass

    def is_processed(self, file_name):
        return file_name in self._data["processed_files"]

    def mark_processed(self, file_name):
        if file_name not in self._data["processed_files"]:
            self._data["processed_files"].append(file_name)
            self.save()

    def add_history(self, entry):
        self._data["history"].append(entry)
        self.save()

    @property
    def processed_count(self):
        return len(self._data["processed_files"])

    def get_stats(self):
        history = self._data.get("history", [])
        kept = sum(1 for h in history if h.get("action") == "keep")
        discarded = sum(1 for h in history if h.get("action") == "discard")
        maybe = sum(1 for h in history if h.get("action") == "maybe")
        return {"kept": kept, "discarded": discarded, "maybe": maybe, "total": len(history)}
