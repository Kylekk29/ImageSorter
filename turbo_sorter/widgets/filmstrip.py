from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
)

from turbo_sorter.theme.styles import get_theme


class ThumbnailFilmstrip(QWidget):
    thumbnail_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._thumb_size = QSize(100, 70)

        self._list = QListWidget()
        self._list.setFlow(QListWidget.Flow.LeftToRight)
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(self._thumb_size)
        self._list.setSpacing(2)
        self._list.setMovement(QListWidget.Movement.Static)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setWrapping(False)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setFixedHeight(90)
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setCursor(Qt.CursorShape.PointingHandCursor)

        self._left_btn = QPushButton("\u25C0")
        self._left_btn.setFixedWidth(24)
        self._left_btn.clicked.connect(self._scroll_left)

        self._right_btn = QPushButton("\u25B6")
        self._right_btn.setFixedWidth(24)
        self._right_btn.clicked.connect(self._scroll_right)

        self._layout.addWidget(self._left_btn)
        self._layout.addWidget(self._list, 1)
        self._layout.addWidget(self._right_btn)

        self.setFixedHeight(90)

    def _scroll_left(self):
        self._list.scrollToItem(
            self._list.item(self._list.currentRow() - 10 if self._list.currentRow() >= 10 else 0),
            QListWidget.ScrollHint.EnsureVisible,
        )

    def _scroll_right(self):
        self._list.scrollToItem(
            self._list.item(
                self._list.currentRow() + 10
                if self._list.currentRow() + 10 < self._list.count()
                else self._list.count() - 1
            ),
            QListWidget.ScrollHint.EnsureVisible,
        )

    def _on_item_clicked(self, item):
        row = self._list.row(item)
        self.thumbnail_clicked.emit(row)

    def set_thumbnails(self, paths, current_index=0):
        self._list.clear()
        for path in paths:
            item = QListWidgetItem()
            item.setSizeHint(self._thumb_size + QSize(0, 8))
            self._list.addItem(item)

        self.set_current_index(current_index)

    def set_thumbnail_pixmap(self, index, pixmap):
        item = self._list.item(index)
        if item:
            item.setIcon(QIcon(pixmap))
            if self._list.currentRow() == index:
                item.setSelected(True)

    def set_current_index(self, index):
        self._list.setCurrentRow(index)
        item = self._list.item(index)
        if item:
            self._list.scrollToItem(item, QListWidget.ScrollHint.EnsureVisible)

    def count(self):
        return self._list.count()
