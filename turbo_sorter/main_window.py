import os
import random
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QColor, QPixmap
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QLineEdit,
    QLabel,
    QStatusBar,
)

from turbo_sorter.core.config import ConfigManager, CROP_PRESETS, APP_NAME
from turbo_sorter.core.image_cache import ImageCache
from turbo_sorter.core.image_loader import (
    ImageLoaderWorker,
    ThumbnailLoader,
    ImageProcessor,
    ImageLoadRequest,
)
from turbo_sorter.core.history import HistoryManager, HistoryEntry
from turbo_sorter.core.session import SessionLogger
from turbo_sorter.core.sorter import FileSorter
from turbo_sorter.theme.styles import make_stylesheet, get_theme
from turbo_sorter.widgets.image_view import ZoomableImageView
from turbo_sorter.widgets.filmstrip import ThumbnailFilmstrip
from turbo_sorter.widgets.info_panel import InfoPanel
from turbo_sorter.dialogs import SettingsDialog, BatchRenameDialog, BatchExportDialog, AboutDialog


class MainWindow(QMainWindow):
    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config
        self._cache = ImageCache(max_size=50)
        self._history = HistoryManager(max_history=config.get("max_history", 200))
        self._session = SessionLogger()
        self._sorter = None

        self._image_loader = ImageLoaderWorker()
        self._thumb_loader = ThumbnailLoader()
        self._image_loader.start()
        self._thumb_loader.start()

        self._image_files = []
        self._current_index = -1
        self._current_pil = None
        self._original_pil = None
        self._current_exif = {}
        self._brightness = 1.0
        self._contrast = 1.0
        self._rotation = 0
        self._current_rating = 0
        self._current_label = ""
        self._current_crop = None
        self._modified = False
        self._slideshow_active = False
        self._search_text = ""
        self._filtered_indices = []
        self._is_loading = False
        self._compare_mode = False
        self._fullscreen_active = False

        self._adjust_timer = QTimer(self)
        self._adjust_timer.setSingleShot(True)
        self._adjust_timer.setInterval(40)
        self._adjust_timer.timeout.connect(self._do_refresh)

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()

        geom = self._config.get("window_geometry", "1400x900")
        try:
            w, h = geom.split("x")
            self.resize(int(w), int(h))
        except (ValueError, AttributeError):
            self.resize(1400, 900)

        last_dir = self._config.get("last_directory", "")
        if last_dir and os.path.isdir(last_dir):
            self.load_folder(last_dir)

        self.apply_theme()

    def _build_ui(self):
        self.setWindowTitle(APP_NAME)

        self._menu_bar = self.menuBar()

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText("Search images by filename... (Ctrl+F)")
        self._search_bar.setVisible(False)
        self._search_bar.setFixedHeight(36)
        self._search_bar.setStyleSheet("margin: 4px 8px;")
        self._search_bar.textChanged.connect(self._on_search)
        self._search_bar.returnPressed.connect(self._search_next)
        main_layout.addWidget(self._search_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        nav_frame = QWidget()
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        self._image_view = ZoomableImageView()
        nav_layout.addWidget(self._image_view, 1)

        self._filmstrip = ThumbnailFilmstrip()
        nav_layout.addWidget(self._filmstrip)

        splitter.addWidget(nav_frame)

        self._info_panel = InfoPanel()
        splitter.addWidget(self._info_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        saved_sizes = self._config.get("splitter_sizes")
        if saved_sizes:
            splitter.setSizes(saved_sizes)
        else:
            splitter.setSizes([900, 320])

        main_layout.addWidget(splitter, 1)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("Ready")
        self._status_bar.addWidget(self._status_label, 1)

        self._compare_overlay = None

        self._build_menus()

    def _build_menus(self):
        def make_action(text, shortcut=None, slot=None):
            act = QAction(text, self)
            if shortcut:
                act.setShortcut(QKeySequence(shortcut))
            if slot:
                act.triggered.connect(slot)
            return act

        file_menu = self._menu_bar.addMenu("&File")
        file_menu.addAction(make_action("Open Folder...", "Ctrl+O", self._open_folder))
        file_menu.addSeparator()
        file_menu.addAction(make_action("Batch Export...", slot=self._batch_export))
        file_menu.addAction(make_action("Batch Rename...", slot=self._batch_rename))
        file_menu.addSeparator()
        file_menu.addAction(make_action("Export Statistics...", slot=self._export_stats))
        file_menu.addSeparator()
        file_menu.addAction(make_action("Quit", "Ctrl+Q", self.close))

        edit_menu = self._menu_bar.addMenu("&Edit")
        self._undo_act = make_action("Undo", "Ctrl+Z", self._undo)
        self._redo_act = make_action("Redo", "Ctrl+Y", self._redo)
        edit_menu.addAction(self._undo_act)
        edit_menu.addAction(self._redo_act)
        edit_menu.addSeparator()
        edit_menu.addAction(make_action("Rotate Right", "R", lambda: self._rotate(90)))
        edit_menu.addAction(make_action("Rotate Left", "L", lambda: self._rotate(-90)))
        edit_menu.addAction(make_action("Auto Adjust", "A", self._auto_adjust))
        edit_menu.addAction(make_action("Reset Adjustments", slot=self._reset_adjustments))

        view_menu = self._menu_bar.addMenu("&View")
        view_menu.addAction(make_action("Fullscreen", "F", self._toggle_fullscreen))
        view_menu.addAction(make_action("Slideshow", "S", self._toggle_slideshow))
        view_menu.addSeparator()
        view_menu.addAction(make_action("Zoom In", "+", self._image_view.zoom_in))
        view_menu.addAction(make_action("Zoom Out", "-", self._image_view.zoom_out))
        view_menu.addAction(make_action("Reset View", "0", self._image_view.reset_view))
        view_menu.addSeparator()
        view_menu.addAction(make_action("Toggle Theme", slot=self._toggle_theme))

        sort_menu = self._menu_bar.addMenu("&Sort")
        sort_menu.addAction(make_action("Keep", "Right", lambda: self._sort("keep")))
        sort_menu.addAction(make_action("Discard", "Down", lambda: self._sort("discard")))
        sort_menu.addAction(make_action("Maybe", "M", lambda: self._sort("maybe")))
        sort_menu.addSeparator()
        sort_menu.addAction(make_action("Compare Mode", "C", self._toggle_compare))

        tools_menu = self._menu_bar.addMenu("&Tools")
        tools_menu.addAction(make_action("Settings...", slot=self._open_settings))
        tools_menu.addSeparator()
        tools_menu.addAction(make_action("About...", slot=self._show_about))

    def _connect_signals(self):
        self._image_loader.finished.connect(self._on_image_loaded)
        self._thumb_loader.finished.connect(self._on_thumb_loaded)
        self._filmstrip.thumbnail_clicked.connect(self._go_to_index)

        panel = self._info_panel
        panel.sort_buttons.sort_action.connect(self._sort)
        panel.brightness_changed.connect(self._on_brightness)
        panel.contrast_changed.connect(self._on_contrast)
        panel.rotate_left.connect(lambda: self._rotate(-90))
        panel.rotate_right.connect(lambda: self._rotate(90))
        panel.auto_adjust.connect(self._auto_adjust)
        panel.crop_requested.connect(self._on_crop)
        panel.reset_adjustments.connect(self._reset_adjustments)
        panel.star_widget.rating_changed.connect(self._on_rating)
        panel.label_widget.label_changed.connect(self._on_label)
        panel.prev_button.clicked.connect(self._go_prev)
        panel.next_button.clicked.connect(self._go_next)

    def _setup_shortcuts(self):
        shortcuts = self._config.get_shortcuts()
        mapping = {
            "keep": lambda: self._sort("keep"),
            "discard": lambda: self._sort("discard"),
            "maybe": lambda: self._sort("maybe"),
            "undo": self._undo,
            "redo": self._redo,
            "rotate_right": lambda: self._rotate(90),
            "rotate_left": lambda: self._rotate(-90),
            "auto_adjust": self._auto_adjust,
            "fullscreen": self._toggle_fullscreen,
            "slideshow": self._toggle_slideshow,
            "zoom_in": self._image_view.zoom_in,
            "zoom_out": self._image_view.zoom_out,
            "reset_view": self._image_view.reset_view,
            "search": self._toggle_search,
            "star_1": lambda: self._set_rating(1),
            "star_2": lambda: self._set_rating(2),
            "star_3": lambda: self._set_rating(3),
            "star_4": lambda: self._set_rating(4),
            "star_5": lambda: self._set_rating(5),
            "compare": self._toggle_compare,
        }
        self._shortcut_actions = []
        for action_name, keys in shortcuts.items():
            fn = mapping.get(action_name)
            if fn and keys:
                for key in keys:
                    try:
                        act = QAction(self)
                        act.setShortcut(QKeySequence(key))
                        act.triggered.connect(fn)
                        self.addAction(act)
                        self._shortcut_actions.append(act)
                    except Exception:
                        pass

    def apply_theme(self):
        dark = self._config.is_dark()
        stylesheet = make_stylesheet(dark)
        self.setStyleSheet(stylesheet)
        self._image_view.viewport().update()

    def _open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder):
        self._config.set("last_directory", folder)
        self._config.save()

        self._image_files = FileSorter.get_image_files(folder)
        if not self._image_files:
            QMessageBox.information(self, "No Images", "No supported images found in this folder.")
            return

        self._sorter = FileSorter(folder)
        self._sorter.ensure_folders()
        self._session.set_folder(folder)

        self._current_index = -1
        self._history.clear()
        self._filtered_indices = list(range(len(self._image_files)))
        self._search_text = ""

        self._cache.clear()
        self._filmstrip.set_thumbnails(
            [self._image_files[i] for i in self._filtered_indices]
        )

        self._load_thumbnails()
        self._go_to_index(0)

        self._status_label.setText(f"Loaded {len(self._image_files)} images from {folder}")

    def _load_thumbnails(self, start=0):
        indices = self._filtered_indices[start:start + 20]
        for i in indices:
            path = self._image_files[i]
            cached = self._cache.get(path)
            if not cached:
                self._thumb_loader.enqueue(path)

    def _on_thumb_loaded(self, path, pixmap):
        if path in self._image_files:
            idx = self._image_files.index(path)
            if idx in self._filtered_indices:
                filtered_idx = self._filtered_indices.index(idx)
                if not pixmap.isNull():
                    from PySide6.QtGui import QIcon
                    item = self._filmstrip._list.item(filtered_idx)
                    if item:
                        item.setIcon(QIcon(pixmap))

    def _go_to_index(self, idx):
        if not self._filtered_indices or idx < 0 or idx >= len(self._filtered_indices):
            return

        self._is_loading = True
        self._current_index = idx
        actual_idx = self._filtered_indices[idx]
        path = self._image_files[actual_idx]

        self._filmstrip.set_current_index(idx)

        cached = self._cache.get(path)
        if cached:
            self._display_image(path, cached)
            self._is_loading = False
        else:
            self._image_view.clear_pixmap()
            self._status_label.setText(f"Loading {os.path.basename(path)}...")
            self._image_loader.enqueue(ImageLoadRequest(path, self._config.get("image_quality", 95)))

        file_name = os.path.basename(path)
        self._image_view.set_filename(file_name)
        self._image_view.set_image_index(f"{idx + 1}/{len(self._filtered_indices)}")
        self._info_panel.set_stats(idx, len(self._filtered_indices))

        if hasattr(self._filmstrip, '_list') and self._filmstrip._list.count() > 0:
            item = self._filmstrip._list.item(idx)
            if item and not item.icon().isNull():
                pass

    def _on_image_loaded(self, result):
        if result.error:
            self._status_label.setText(f"Error: {result.error}")
            self._is_loading = False
            return

        actual_idx = self._image_files.index(result.path) if result.path in self._image_files else -1
        if actual_idx < 0:
            self._is_loading = False
            return

        if actual_idx in self._filtered_indices:
            filtered_idx = self._filtered_indices.index(actual_idx)
            if filtered_idx == self._current_index:
                self._display_image(result.path, result.pixmap)
                self._current_pil = result.pil_image.copy()
                self._original_pil = result.pil_image.copy()
                self._current_exif = result.exif
                self._info_panel.set_exif(result.exif)

        self._cache.put(result.path, result.pixmap)
        self._is_loading = False

    def _display_image(self, path, pixmap):
        self._image_view.set_pixmap(pixmap)
        self._image_view.set_rating(self._current_rating)
        self._image_view.set_color_label(self._current_label)

    def _go_prev(self):
        if self._current_index > 0:
            self._go_to_index(self._current_index - 1)

    def _go_next(self):
        if self._current_index < len(self._filtered_indices) - 1:
            self._go_to_index(self._current_index + 1)

    def _sort(self, action):
        if self._current_index < 0 or not self._filtered_indices or not self._sorter:
            return

        actual_idx = self._filtered_indices[self._current_index]
        path = self._image_files[actual_idx]
        file_name = os.path.basename(path)

        self._sorter.sort_file(path, action, file_name)

        if self._modified and self._current_pil:
            quality = self._config.get("image_quality", 95)
            self._sorter.save_modified(self._current_pil, action, file_name, quality)

        log_entry = {
            "file": file_name,
            "action": action,
            "rating": self._current_rating,
            "label": self._current_label,
        }
        self._session.add_history(log_entry)
        self._session.mark_processed(file_name)

        self._history.push(HistoryEntry(
            file_path=path,
            action=action,
            rating=self._current_rating,
            label=self._current_label,
            description=f"{action.title()}: {file_name}",
        ))

        overlay_colors = {
            "keep": QColor(46, 204, 113),
            "discard": QColor(231, 76, 60),
            "maybe": QColor(243, 156, 18),
        }
        overlay_texts = {
            "keep": "\u2714 KEPT",
            "discard": "\u2718 DISCARDED",
            "maybe": "\u2753 MAYBE",
        }
        self._image_view.set_overlay(
            overlay_texts.get(action, ""),
            overlay_colors.get(action, QColor(255, 255, 255)),
            duration_sec=0.6,
        )

        self._modified = False
        self._image_view.set_modification_badge("")

        if self._current_index < len(self._filtered_indices) - 1:
            next_index = self._current_index + 1
            prefetch_idx = next_index + 1
            if prefetch_idx < len(self._filtered_indices):
                prefetch_actual = self._filtered_indices[prefetch_idx]
                prefetch_path = self._image_files[prefetch_actual]
                if not self._cache.contains(prefetch_path):
                    self._image_loader.enqueue(
                        ImageLoadRequest(prefetch_path, self._config.get("image_quality", 95))
                    )
            self._go_to_index(next_index)
        else:
            self._show_finished()

    def _show_finished(self):
        self._image_view.set_overlay(
            "ALL DONE! \u2705",
            QColor(46, 204, 113),
            duration_sec=2,
        )
        stats = self._session.get_stats()
        self._status_label.setText(
            f"Finished! Kept: {stats['kept']} | Discarded: {stats['discarded']} | Maybe: {stats['maybe']}"
        )

    def _undo(self):
        entry = self._history.undo()
        if entry:
            self._status_label.setText(f"Undo: {entry.description}")

    def _redo(self):
        entry = self._history.redo()
        if entry:
            self._status_label.setText(f"Redo: {entry.description}")

    def _on_brightness(self, value):
        self._brightness = value
        self._modified = True
        self._image_view.set_modification_badge("Modified")
        self._adjust_timer.start()

    def _on_contrast(self, value):
        self._contrast = value
        self._modified = True
        self._image_view.set_modification_badge("Modified")
        self._adjust_timer.start()

    def _do_refresh(self):
        self._refresh_current_image()

    def _rotate(self, degrees):
        self._rotation = (self._rotation + degrees) % 360
        self._modified = True
        self._image_view.set_modification_badge(f"Rotated {self._rotation}\u00b0")
        self._refresh_current_image()

    def _auto_adjust(self):
        if self._current_pil:
            self._original_pil = self._current_pil.copy()
            self._current_pil = ImageProcessor.auto_adjust(self._current_pil)
            self._modified = True
            self._image_view.set_modification_badge("Auto-Adjusted")
            self._info_panel.reset_sliders()
            self._brightness = 1.0
            self._contrast = 1.0
            self._rotation = 0
            pixmap = ImageProcessor.pil_to_pixmap(self._current_pil)
            self._image_view.set_pixmap(pixmap)

    def _reset_adjustments(self):
        if self._original_pil:
            self._current_pil = self._original_pil.copy()
        self._brightness = 1.0
        self._contrast = 1.0
        self._rotation = 0
        self._current_crop = None
        self._modified = False
        self._image_view.set_modification_badge("")
        self._info_panel.reset_sliders()
        pixmap = ImageProcessor.pil_to_pixmap(self._current_pil)
        self._image_view.set_pixmap(pixmap)

    def _on_crop(self, preset_name):
        ratios = CROP_PRESETS.get(preset_name)
        if ratios and self._current_pil:
            self._current_pil = ImageProcessor.crop_to_aspect(
                self._current_pil, ratios[0], ratios[1]
            )
            self._modified = True
            self._image_view.set_modification_badge(f"Cropped ({preset_name})")
            pixmap = ImageProcessor.pil_to_pixmap(self._current_pil)
            self._image_view.set_pixmap(pixmap)

    def _refresh_current_image(self):
        if self._current_pil:
            img = ImageProcessor.adjust_image(
                self._current_pil, self._brightness, self._contrast, self._rotation
            )
            pixmap = ImageProcessor.pil_to_pixmap(img)
            self._image_view.set_pixmap(pixmap)

    def _on_rating(self, rating):
        self._current_rating = rating
        self._image_view.set_rating(rating)

    def _set_rating(self, rating):
        self._current_rating = rating if rating != self._current_rating else 0
        self._info_panel.star_widget.set_rating(self._current_rating)
        self._image_view.set_rating(self._current_rating)

    def _on_label(self, label):
        self._current_label = label
        self._image_view.set_color_label(label)

    def _on_search(self, text):
        self._search_text = text.lower().strip()
        self._filter_images()

    def _search_next(self):
        pass

    def _toggle_search(self):
        visible = not self._search_bar.isVisible()
        self._search_bar.setVisible(visible)
        if visible:
            self._search_bar.setFocus()
        else:
            self._search_bar.clear()
            self._filter_images()

    def _filter_images(self):
        if not self._search_text:
            self._filtered_indices = list(range(len(self._image_files)))
        else:
            self._filtered_indices = [
                i for i in range(len(self._image_files))
                if self._search_text in os.path.basename(self._image_files[i]).lower()
            ]

        self._filmstrip.set_thumbnails(
            [self._image_files[i] for i in self._filtered_indices]
        )
        self._load_thumbnails()

        if self._filtered_indices:
            self._go_to_index(0)
        else:
            self._image_view.clear_pixmap()
            self._image_view.set_filename("")
            self._image_view.set_image_index("")
            self._info_panel.set_stats(0, 0)
            self._info_panel.clear_exif()

        count = len(self._filtered_indices)
        self._status_label.setText(
            f"Found {count} match{'es' if count != 1 else ''}"
            if self._search_text
            else f"{len(self._image_files)} images"
        )

    def _toggle_compare(self):
        self._compare_mode = not self._compare_mode
        if self._compare_mode:
            self._show_compare()
        else:
            self._hide_compare()

    def _show_compare(self):
        if self._current_index < len(self._filtered_indices) - 1:
            current_path = self._image_files[self._filtered_indices[self._current_index]]
            next_path = self._image_files[self._filtered_indices[self._current_index + 1]]
            current_pix = self._cache.get(current_path)
            next_pix = self._cache.get(next_path)
            if current_pix and next_pix:
                self._image_view.set_overlay("COMPARE MODE - C to exit", QColor(255, 255, 255))
                self._status_label.setText("Compare Mode: Use Left/Right to switch images")

    def _hide_compare(self):
        self._image_view.set_overlay("")
        self._image_view.set_pixmap(QPixmap())
        if self._current_index >= 0 and self._filtered_indices:
            actual_idx = self._filtered_indices[self._current_index]
            cached = self._cache.get(self._image_files[actual_idx])
            if cached:
                self._image_view.set_pixmap(cached)

    def _toggle_fullscreen(self):
        if self._fullscreen_active:
            self.showNormal()
            self._menu_bar.setVisible(True)
            self._filmstrip.setVisible(True)
            self._info_panel.setVisible(True)
            self._status_bar.setVisible(True)
            self._fullscreen_active = False
        else:
            self.showFullScreen()
            self._menu_bar.setVisible(False)
            self._filmstrip.setVisible(False)
            self._info_panel.setVisible(False)
            self._status_bar.setVisible(False)
            self._fullscreen_active = True

    def _toggle_slideshow(self):
        if self._slideshow_active:
            self._stop_slideshow()
        else:
            self._start_slideshow()

    def _start_slideshow(self):
        if len(self._filtered_indices) < 1:
            return
        self._slideshow_active = True
        delay = self._config.get("slideshow_delay", 3) * 1000
        self._slideshow_timer = QTimer(self)
        self._slideshow_timer.timeout.connect(self._slideshow_next)
        self._slideshow_timer.start(delay)
        self._status_label.setText("Slideshow playing... (S to stop)")
        self._slideshow_current_start = self._current_index

    def _stop_slideshow(self):
        self._slideshow_active = False
        if hasattr(self, '_slideshow_timer'):
            self._slideshow_timer.stop()
        self._status_label.setText("Slideshow stopped")

    def _slideshow_next(self):
        if not self._slideshow_active:
            return
        shuffle = self._config.get("slideshow_shuffle", False)
        loop = self._config.get("slideshow_loop", True)
        if shuffle:
            idx = random.randint(0, len(self._filtered_indices) - 1)
            self._go_to_index(idx)
        elif self._current_index < len(self._filtered_indices) - 1:
            self._go_to_index(self._current_index + 1)
        elif loop:
            self._go_to_index(0)
        else:
            self._stop_slideshow()

    def _toggle_theme(self):
        self._config.set("dark", not self._config.is_dark())
        self._config.save()
        self.apply_theme()

    def _open_settings(self):
        dialog = SettingsDialog(self._config, self)
        dialog.exec()

    def _show_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def _batch_rename(self):
        if not self._sorter:
            QMessageBox.information(self, "Info", "Open a folder first.")
            return
        dialog = BatchRenameDialog(self._sorter.base_folder, self)
        if dialog.exec():
            pattern = dialog.get_pattern()
            self._status_label.setText(f"Batch rename complete with pattern: {pattern}")

    def _batch_export(self):
        if not self._sorter or not self._image_files:
            QMessageBox.information(self, "Info", "Open a folder first.")
            return
        dialog = BatchExportDialog(self)
        if dialog.exec():
            dest = dialog.get_path()
            count = 0
            for i in self._filtered_indices:
                path = self._image_files[i]
                file_name = os.path.basename(path)
                try:
                    import shutil
                    shutil.copy2(path, os.path.join(dest, file_name))
                    count += 1
                except (shutil.Error, IOError):
                    pass
            QMessageBox.information(
                self, "Export Complete",
                f"Exported {count} of {len(self._filtered_indices)} images to:\n{dest}"
            )

    def _export_stats(self):
        if not self._sorter or not self._image_files:
            QMessageBox.information(self, "Info", "Open a folder first.")
            return
        stats_text = FileSorter.generate_stats(
            self._session._data.get("history", []),
            self._sorter.base_folder,
        )
        stats_path = os.path.join(self._sorter.base_folder, "turbo_sorter_statistics.txt")
        try:
            with open(stats_path, "w") as f:
                f.write(stats_text)
            QMessageBox.information(
                self, "Statistics Exported",
                f"Statistics saved to:\n{stats_path}"
            )
        except IOError:
            QMessageBox.warning(self, "Error", "Could not save statistics file.")

    def closeEvent(self, event):
        self._image_loader.stop()
        self._thumb_loader.stop()
        self._config.set("window_geometry", f"{self.width()}x{self.height()}")
        sizes = getattr(self, 'centralWidget', None)
        for w in self.findChildren(QSplitter):
            self._config.set("splitter_sizes", w.sizes())
            break
        self._config.save()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self._slideshow_active:
                self._stop_slideshow()
            elif self._fullscreen_active:
                self._toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Left and not self._search_bar.hasFocus():
            self._go_prev()
        elif event.key() == Qt.Key.Key_Right and not self._search_bar.hasFocus():
            self._go_next()
        super().keyPressEvent(event)
