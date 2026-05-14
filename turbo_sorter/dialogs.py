import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QTabWidget,
    QWidget,
    QLineEdit,
    QFileDialog,
    QTextEdit,
    QGroupBox,
    QDialogButtonBox,
    QFormLayout,
    QMessageBox,
)

from turbo_sorter.core.config import ConfigManager, APP_NAME, VERSION


class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Settings")
        self.setMinimumSize(480, 400)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)

        self._quality_spin = QSpinBox()
        self._quality_spin.setRange(10, 100)
        self._quality_spin.setValue(self._config.get("image_quality", 95))
        general_layout.addRow("Image Quality:", self._quality_spin)

        self._prefetch_spin = QSpinBox()
        self._prefetch_spin.setRange(0, 20)
        self._prefetch_spin.setValue(self._config.get("prefetch_count", 3))
        general_layout.addRow("Prefetch Count:", self._prefetch_spin)

        self._history_spin = QSpinBox()
        self._history_spin.setRange(10, 1000)
        self._history_spin.setValue(self._config.get("max_history", 200))
        general_layout.addRow("Max History:", self._history_spin)

        tabs.addTab(general_tab, "General")

        slideshow_tab = QWidget()
        slideshow_layout = QFormLayout(slideshow_tab)

        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(1, 60)
        self._delay_spin.setValue(self._config.get("slideshow_delay", 3))
        self._delay_spin.setSuffix(" sec")
        slideshow_layout.addRow("Delay:", self._delay_spin)

        self._loop_check = QCheckBox("Loop slideshow")
        self._loop_check.setChecked(self._config.get("slideshow_loop", True))
        slideshow_layout.addRow(self._loop_check)

        self._shuffle_check = QCheckBox("Shuffle images")
        self._shuffle_check.setChecked(self._config.get("slideshow_shuffle", False))
        slideshow_layout.addRow(self._shuffle_check)

        tabs.addTab(slideshow_tab, "Slideshow")

        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)
        about_text = QLabel(
            f"<h2>{APP_NAME}</h2>"
            f"<p>Version {VERSION}</p>"
            f"<p>A professional image sorting tool for photographers.</p>"
            f"<p>Built with PySide6, Pillow, and Python.</p>"
            f"<hr>"
            f"<p><b>Keyboard Shortcuts:</b></p>"
            f"<p>"
            f"\u2192 / Space - Keep<br>"
            f"\u2193 / N - Discard<br>"
            f"M - Maybe<br>"
            f"Ctrl+Z - Undo<br>"
            f"Ctrl+Y - Redo<br>"
            f"F - Fullscreen<br>"
            f"S - Slideshow<br>"
            f"R - Rotate Right<br>"
            f"L - Rotate Left<br>"
            f"A - Auto Adjust<br>"
            f"+/- - Zoom In/Out<br>"
            f"0 - Reset View<br>"
            f"1-5 - Star Rating<br>"
            f"Ctrl+F - Search<br>"
            f"C - Compare<br>"
            f"</p>"
        )
        about_text.setWordWrap(True)
        about_text.setTextFormat(Qt.TextFormat.RichText)
        about_layout.addWidget(about_text)
        about_layout.addStretch(1)
        tabs.addTab(about_tab, "About")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        self._config.set("image_quality", self._quality_spin.value())
        self._config.set("prefetch_count", self._prefetch_spin.value())
        self._config.set("max_history", self._history_spin.value())
        self._config.set("slideshow_delay", self._delay_spin.value())
        self._config.set("slideshow_loop", self._loop_check.isChecked())
        self._config.set("slideshow_shuffle", self._shuffle_check.isChecked())
        self._config.save()
        self.accept()


class BatchRenameDialog(QDialog):
    def __init__(self, folder_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Rename")
        self.setMinimumSize(400, 150)
        self._folder_path = folder_path
        self._result_pattern = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Rename pattern (use {n} for counter):"))
        layout.addWidget(QLabel('Example: "Photo_{n:03d}" -> Photo_001, Photo_002...'))

        self._pattern_input = QLineEdit()
        self._pattern_input.setPlaceholderText("e.g. Wedding_{n:03d}")
        layout.addWidget(self._pattern_input)

        self._preview_label = QLabel("Preview: ")
        layout.addWidget(self._preview_label)

        self._pattern_input.textChanged.connect(self._update_preview)

        buttons = QHBoxLayout()
        rename_btn = QPushButton("Rename")
        rename_btn.clicked.connect(self._on_rename)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(rename_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def _update_preview(self):
        pattern = self._pattern_input.text()
        if "{n}" in pattern:
            self._preview_label.setText(
                f"Preview: {pattern.replace('{n}', '001')}, {pattern.replace('{n}', '002')}"
            )
        else:
            self._preview_label.setText(f"Preview: {pattern} (no counter)")

    def _on_rename(self):
        pattern = self._pattern_input.text().strip()
        if not pattern:
            QMessageBox.warning(self, "Error", "Please enter a rename pattern.")
            return
        if "{n}" not in pattern:
            reply = QMessageBox.question(
                self, "No Counter", "Pattern has no {n} counter. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._result_pattern = pattern
        self.accept()

    def get_pattern(self):
        return self._result_pattern


class BatchExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Export")
        self.setMinimumSize(450, 200)
        self._result_path = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Export unsorted images to a destination folder."))

        path_row = QHBoxLayout()
        self._path_display = QLineEdit()
        self._path_display.setReadOnly(True)
        self._path_display.setPlaceholderText("Select destination folder...")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self._path_display, 1)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        buttons = QHBoxLayout()
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._on_export)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(export_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if folder:
            self._path_display.setText(folder)

    def _on_export(self):
        path = self._path_display.text().strip()
        if not path:
            QMessageBox.warning(self, "Error", "Please select a destination folder.")
            return
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Invalid folder path.")
            return
        self._result_path = path
        self.accept()

    def get_path(self):
        return self._result_path


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setFixedSize(400, 300)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(f"<h1>{APP_NAME}</h1>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = QLabel(f"<p style='font-size: 16px;'>Version {VERSION}</p>")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        desc = QLabel(
            "A professional image sorting tool for photographers.\n\n"
            "Built with PySide6, Pillow, and Python."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addStretch(1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
