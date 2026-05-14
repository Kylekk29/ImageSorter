from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen, QBrush, QMouseEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTextEdit,
    QGroupBox,
    QButtonGroup,
    QSizePolicy,
    QFrame,
)

from turbo_sorter.theme.styles import get_theme, COLOR_LABEL_COLORS


class StarRating(QWidget):
    rating_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rating = 0
        self._hover = 0
        self._star_size = 22
        self._spacing = 4
        self.setFixedHeight(self._star_size + 8)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_rating(self, rating):
        self._rating = rating
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = get_theme(True)
        font = QFont()
        font.setPointSize(14)
        painter.setFont(font)

        for i in range(5):
            x = i * (self._star_size + self._spacing) + 4
            y = 4
            filled = i < (self._hover if self._hover > 0 else self._rating)
            if filled:
                painter.setPen(QPen(QColor(t["star"]), 1))
                painter.setBrush(QBrush(QColor(t["star"])))
            else:
                painter.setPen(QPen(QColor(t["text_muted"]), 1))
                painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
            painter.drawText(x, y + self._star_size, "\u2605")

    def mouseMoveEvent(self, event):
        idx = int(event.position().x() // (self._star_size + self._spacing)) + 1
        if 1 <= idx <= 5 and idx != self._hover:
            self._hover = idx
            self.update()

    def leaveEvent(self, event):
        self._hover = 0
        self.update()

    def mousePressEvent(self, event):
        idx = int(event.position().x() // (self._star_size + self._spacing)) + 1
        if 1 <= idx <= 5:
            self._rating = idx if idx != self._rating else 0
            self.rating_changed.emit(self._rating)
            self.update()

    def sizeHint(self):
        w = 5 * self._star_size + 4 * self._spacing + 8
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        w = 5 * self._star_size + 4 * self._spacing + 8
        from PySide6.QtCore import QSize
        return QSize(w, self._star_size + 8)


class ColorLabelWidget(QWidget):
    label_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected = ""
        self._label_size = 24
        self._spacing = 6
        self._labels = list(COLOR_LABEL_COLORS.keys())
        self._colors = list(COLOR_LABEL_COLORS.values())
        self.setFixedHeight(self._label_size + 12)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_label(self, label):
        self._selected = label
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for i, (name, color) in enumerate(zip(self._labels, self._colors)):
            x = i * (self._label_size + self._spacing) + 6
            y = 6
            c = QColor(color)
            painter.setPen(QPen(c.darker(130), 2 if name == self._selected else 1))
            painter.setBrush(QBrush(c))
            r = self._label_size // 2
            painter.drawEllipse(x + r - r, y + r - r, self._label_size, self._label_size)

            if name == self._selected:
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                font = QFont()
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(x, y + self._label_size - 4, "\u2713")

    def mousePressEvent(self, event):
        idx = int((event.position().x() - 6) // (self._label_size + self._spacing))
        if 0 <= idx < len(self._labels):
            name = self._labels[idx]
            self._selected = name if name != self._selected else ""
            self.label_changed.emit(self._selected)
            self.update()

    def sizeHint(self):
        from PySide6.QtCore import QSize
        w = len(self._labels) * (self._label_size + self._spacing) + 12
        return QSize(w, self._label_size + 12)

    def minimumSizeHint(self):
        return self.sizeHint()


class SortButtonBar(QWidget):
    sort_action = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._keep_btn = QPushButton("\u2714 Keep")
        self._keep_btn.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: white; font-weight: bold; padding: 10px 20px; border: none; border-radius: 8px; font-size: 14px; }"
            "QPushButton:hover { background-color: #27ae60; }"
            "QPushButton:pressed { background-color: #1e8449; }"
        )
        self._keep_btn.clicked.connect(lambda: self.sort_action.emit("keep"))

        self._maybe_btn = QPushButton("\u2753 Maybe")
        self._maybe_btn.setStyleSheet(
            "QPushButton { background-color: #f39c12; color: white; font-weight: bold; padding: 10px 20px; border: none; border-radius: 8px; font-size: 14px; }"
            "QPushButton:hover { background-color: #e67e22; }"
            "QPushButton:pressed { background-color: #d35400; }"
        )
        self._maybe_btn.clicked.connect(lambda: self.sort_action.emit("maybe"))

        self._discard_btn = QPushButton("\u2718 Discard")
        self._discard_btn.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; font-weight: bold; padding: 10px 20px; border: none; border-radius: 8px; font-size: 14px; }"
            "QPushButton:hover { background-color: #c0392b; }"
            "QPushButton:pressed { background-color: #a93226; }"
        )
        self._discard_btn.clicked.connect(lambda: self.sort_action.emit("discard"))

        layout.addWidget(self._keep_btn)
        layout.addWidget(self._maybe_btn)
        layout.addWidget(self._discard_btn)


class InfoPanel(QWidget):
    brightness_changed = Signal(float)
    contrast_changed = Signal(float)
    rotate_left = Signal()
    rotate_right = Signal()
    auto_adjust = Signal()
    crop_requested = Signal(str)
    reset_adjustments = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        sort_group = QGroupBox("Sort Action")
        sort_layout = QVBoxLayout(sort_group)
        self._sort_buttons = SortButtonBar()
        sort_layout.addWidget(self._sort_buttons)
        layout.addWidget(sort_group)

        exif_group = QGroupBox("Image Info")
        exif_layout = QVBoxLayout(exif_group)
        self._exif_display = QTextEdit()
        self._exif_display.setReadOnly(True)
        self._exif_display.setMaximumHeight(200)
        self._exif_display.setPlaceholderText("EXIF data will appear here...")
        exif_layout.addWidget(self._exif_display)
        layout.addWidget(exif_group)

        rating_group = QGroupBox("Rating")
        rating_layout = QVBoxLayout(rating_group)
        self._star_widget = StarRating()
        rating_layout.addWidget(self._star_widget)
        layout.addWidget(rating_group)

        label_group = QGroupBox("Color Label")
        label_layout = QVBoxLayout(label_group)
        self._label_widget = ColorLabelWidget()
        label_layout.addWidget(self._label_widget)
        layout.addWidget(label_group)

        adjust_group = QGroupBox("Adjustments")
        adjust_layout = QVBoxLayout(adjust_group)

        self._brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self._brightness_slider.setRange(0, 200)
        self._brightness_slider.setValue(100)
        self._brightness_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self._brightness_slider.valueChanged.connect(self._on_brightness_slider)
        self._brightness_slider.sliderReleased.connect(self._on_brightness_release)
        brightness_row = QHBoxLayout()
        brightness_row.addWidget(QLabel("\u2600"))
        brightness_row.addWidget(self._brightness_slider, 1)
        self._brightness_label = QLabel("1.0")
        self._brightness_label.setFixedWidth(30)
        brightness_row.addWidget(self._brightness_label)
        adjust_layout.addLayout(brightness_row)

        self._contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self._contrast_slider.setRange(0, 200)
        self._contrast_slider.setValue(100)
        self._contrast_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self._contrast_slider.valueChanged.connect(self._on_contrast_slider)
        self._contrast_slider.sliderReleased.connect(self._on_contrast_release)
        contrast_row = QHBoxLayout()
        contrast_row.addWidget(QLabel("\u25D0"))
        contrast_row.addWidget(self._contrast_slider, 1)
        self._contrast_label = QLabel("1.0")
        self._contrast_label.setFixedWidth(30)
        contrast_row.addWidget(self._contrast_label)
        adjust_layout.addLayout(contrast_row)

        crop_row = QHBoxLayout()
        preset_btn = QPushButton("Crop")
        crop_row.addWidget(preset_btn)
        from turbo_sorter.core.config import CROP_PRESETS
        self._crop_combo = QLabel("1:1 Square")
        crop_row.addWidget(self._crop_combo, 1)
        adjust_layout.addLayout(crop_row)

        btn_row1 = QHBoxLayout()
        self._auto_btn = QPushButton("Auto Adjust")
        self._reset_btn = QPushButton("Reset")
        self._rotate_l_btn = QPushButton("\u21BA L")
        self._rotate_r_btn = QPushButton("R \u21BB")
        btn_row1.addWidget(self._auto_btn)
        btn_row1.addWidget(self._reset_btn)
        btn_row1.addWidget(self._rotate_l_btn)
        btn_row1.addWidget(self._rotate_r_btn)
        adjust_layout.addLayout(btn_row1)

        self._auto_btn.clicked.connect(self.auto_adjust.emit)
        self._reset_btn.clicked.connect(self.reset_adjustments.emit)
        self._rotate_l_btn.clicked.connect(self.rotate_left.emit)
        self._rotate_r_btn.clicked.connect(self.rotate_right.emit)
        preset_btn.clicked.connect(self._cycle_crop)

        self._current_crop_idx = 0
        self._crop_keys = list(CROP_PRESETS.keys())

        layout.addWidget(adjust_group)

        nav_group = QGroupBox("Navigation")
        nav_layout = QHBoxLayout(nav_group)
        self._prev_btn = QPushButton("\u25C0 Previous")
        self._next_btn = QPushButton("Next \u25B6")
        nav_layout.addWidget(self._prev_btn)
        nav_layout.addWidget(self._next_btn)
        layout.addWidget(nav_group)

        self._stats_label = QLabel("No images loaded")
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stats_label.setStyleSheet("color: #6c7086; font-size: 11px; padding: 4px;")
        layout.addWidget(self._stats_label)

        layout.addStretch(1)

    def _on_brightness_slider(self, value):
        val = value / 100.0
        self._brightness_label.setText(f"{val:.1f}")
        self.brightness_changed.emit(val)

    def _on_brightness_release(self):
        self.brightness_changed.emit(self._brightness_slider.value() / 100.0)

    def _on_contrast_slider(self, value):
        val = value / 100.0
        self._contrast_label.setText(f"{val:.1f}")
        self.contrast_changed.emit(val)

    def _on_contrast_release(self):
        self.contrast_changed.emit(self._contrast_slider.value() / 100.0)

    def _cycle_crop(self):
        self._current_crop_idx = (self._current_crop_idx + 1) % len(self._crop_keys)
        key = self._crop_keys[self._current_crop_idx]
        self._crop_combo.setText(key)
        self.crop_requested.emit(key)

    def set_exif(self, exif_data):
        text = ""
        for key, val in exif_data.items():
            text += f"<b>{key}:</b> {val}<br>"
        self._exif_display.setHtml(text)

    def clear_exif(self):
        self._exif_display.clear()

    def set_stats(self, current, total):
        self._stats_label.setText(f"Image {current + 1} of {total}" if total else "No images")

    def reset_sliders(self):
        self._brightness_slider.setValue(100)
        self._contrast_slider.setValue(100)
        self._brightness_label.setText("1.0")
        self._contrast_label.setText("1.0")

    @property
    def sort_buttons(self):
        return self._sort_buttons

    @property
    def star_widget(self):
        return self._star_widget

    @property
    def label_widget(self):
        return self._label_widget

    @property
    def prev_button(self):
        return self._prev_btn

    @property
    def next_button(self):
        return self._next_btn
