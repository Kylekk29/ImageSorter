import json
import os

CONFIG_FILE = "turbo_sorter_config.json"
APP_NAME = "Turbo Photo Sorter"
VERSION = "5.0.0"

COLOR_LABELS = {
    "red": "#e74c3c",
    "yellow": "#f1c40f",
    "green": "#2ecc71",
    "blue": "#3498db",
    "purple": "#9b59b6",
}

CROP_PRESETS = {
    "Square (1:1)": (1, 1),
    "HD (16:9)": (16, 9),
    "Standard (4:3)": (4, 3),
    "Classic (3:2)": (3, 2),
    "Ultrawide (21:9)": (21, 9),
}

DEFAULT_CONFIG = {
    "dark": True,
    "slideshow_delay": 3,
    "image_quality": 95,
    "prefetch_count": 3,
    "max_history": 200,
    "last_directory": "",
    "window_geometry": "1400x900",
    "splitter_sizes": None,
    "shortcuts": {
        "keep": ["Right", "space", "k"],
        "discard": ["Down", "n"],
        "maybe": ["m"],
        "undo": ["Ctrl+z"],
        "redo": ["Ctrl+y"],
        "rotate_right": ["r"],
        "rotate_left": ["l"],
        "auto_adjust": ["a"],
        "fullscreen": ["f"],
        "slideshow": ["s"],
        "zoom_in": ["+", "="],
        "zoom_out": ["-"],
        "reset_view": ["0"],
        "search": ["Ctrl+f"],
        "star_1": ["1"],
        "star_2": ["2"],
        "star_3": ["3"],
        "star_4": ["4"],
        "star_5": ["5"],
        "compare": ["c"],
    },
    "slideshow_loop": True,
    "slideshow_shuffle": False,
}


class ConfigManager:
    def __init__(self):
        self.config = dict(DEFAULT_CONFIG)
        self.load()

    @property
    def config_path(self):
        return os.path.join(os.getcwd(), CONFIG_FILE)

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    loaded = json.load(f)
                self.config = {**self.config, **loaded}
            except (json.JSONDecodeError, IOError):
                pass

    def save(self):
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except IOError:
            pass

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value

    def get_shortcuts(self):
        return self.config.get("shortcuts", DEFAULT_CONFIG["shortcuts"])

    def is_dark(self):
        return self.config.get("dark", True)
