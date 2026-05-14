from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QPen,
    QColor,
    QFont,
    QFontMetrics,
)
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QWidget, QVBoxLayout

from turbo_sorter.theme.styles import get_theme


class ZoomableImageView(QGraphicsView):
    zoom_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)

        self._zoom = 1.0
        self._min_zoom = 0.05
        self._max_zoom = 20.0
        self._fit_mode = True
        self._dragging = False
        self._drag_start = None
        self._pan_start = None

        self._overlay_text = ""
        self._overlay_color = QColor(255, 255, 255)
        self._overlay_visible = False
        self._overlay_timer = 0

        self._filename_text = ""
        self._image_index_text = ""
        self._modification_badge = ""
        self._rating = 0
        self._color_label = ""

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.setAcceptDrops(False)
        self.setStyleSheet("background: transparent; border: none;")

    def set_pixmap(self, pixmap):
        self._pixmap_item.setPixmap(pixmap)
        if pixmap and not pixmap.isNull():
            self._scene.setSceneRect(QRectF(pixmap.rect()))
            if self._fit_mode:
                self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
                self._zoom = 1.0
        else:
            self._scene.setSceneRect(QRectF(0, 0, 100, 100))

    def clear_pixmap(self):
        self._pixmap_item.setPixmap(QPixmap())

    def current_pixmap(self):
        return self._pixmap_item.pixmap()

    def set_overlay(self, text, color=None, duration_sec=0):
        self._overlay_text = text
        if color:
            self._overlay_color = color
        self._overlay_visible = True
        self._overlay_timer = duration_sec
        if duration_sec > 0:
            from PySide6.QtCore import QTimer, QTimeLine
            QTimer.singleShot(int(duration_sec * 1000), self._clear_overlay)
        self.viewport().update()

    def _clear_overlay(self):
        self._overlay_visible = False
        self.viewport().update()

    def set_filename(self, text):
        self._filename_text = text
        self.viewport().update()

    def set_image_index(self, text):
        self._image_index_text = text
        self.viewport().update()

    def set_modification_badge(self, text):
        self._modification_badge = text
        self.viewport().update()

    def set_rating(self, rating):
        self._rating = rating
        self.viewport().update()

    def set_color_label(self, label):
        self._color_label = label
        self.viewport().update()

    def reset_view(self):
        self._fit_mode = True
        self.resetTransform()
        if self._pixmap_item.pixmap() and not self._pixmap_item.pixmap().isNull():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = 1.0
        self.zoom_changed.emit(1.0)

    def zoom_in(self):
        self._fit_mode = False
        self._apply_zoom(1.25)

    def zoom_out(self):
        self._fit_mode = False
        self._apply_zoom(0.8)

    def _apply_zoom(self, factor):
        new_zoom = self._zoom * factor
        if self._min_zoom <= new_zoom <= self._max_zoom:
            self._zoom = new_zoom
            self.scale(factor, factor)
            self.zoom_changed.emit(self._zoom)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._zoom > 1.1:
                self._dragging = True
                self._drag_start = event.pos()
                self._pan_start = (self.horizontalScrollBar().value(), self.verticalScrollBar().value())
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                super().mousePressEvent(event)
        elif event.button() == Qt.MouseButton.RightButton:
            if self._zoom > 1.1:
                self._fit_mode = True
                self.reset_view()

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_start:
            dx = event.pos().x() - self._drag_start.x()
            dy = event.pos().y() - self._drag_start.y()
            self.horizontalScrollBar().setValue(self._pan_start[0] - dx)
            self.verticalScrollBar().setValue(self._pan_start[1] - dy)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self._drag_start = None
            self._pan_start = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.reset_view()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_mode and self._pixmap_item.pixmap() and not self._pixmap_item.pixmap().isNull():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def drawForeground(self, painter, rect):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._overlay_visible and self._overlay_text:
            font = QFont()
            font.setPointSize(48)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(self._overlay_color, 2))
            fm = QFontMetrics(font)
            text = self._overlay_text
            tw = fm.horizontalAdvance(text)
            th = fm.height()
            x = (self.width() - tw) // 2
            y = (self.height() - th) // 2
            painter.setOpacity(0.9)
            painter.drawText(x, y + fm.ascent(), text)
            painter.setOpacity(1.0)

        font = QFont()
        font.setPointSize(11)

        if self._filename_text:
            font.setPointSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            painter.setOpacity(0.85)
            fm = QFontMetrics(font)
            text = self._filename_text
            tw = fm.horizontalAdvance(text)
            x = 16
            y = self.height() - 20
            painter.fillRect(x - 6, y - fm.ascent() - 6, tw + 12, fm.height() + 12, QColor(0, 0, 0, 160))
            painter.drawText(x, y, text)
            painter.setOpacity(1.0)

        if self._image_index_text:
            font.setPointSize(11)
            font.setBold(False)
            painter.setFont(font)
            fm = QFontMetrics(font)
            text = self._image_index_text
            tw = fm.horizontalAdvance(text)
            x = self.width() - tw - 20
            y = 20 + fm.ascent()
            painter.fillRect(x - 8, y - fm.ascent() - 6, tw + 16, fm.height() + 12, QColor(0, 0, 0, 160))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(x, y, text)

        if self._rating > 0:
            font.setPointSize(14)
            painter.setFont(font)
            stars = "★" * self._rating + "☆" * (5 - self._rating)
            fm = QFontMetrics(font)
            tw = fm.horizontalAdvance(stars)
            x = self.width() - tw - 20
            y = 20 + 30 + fm.ascent()
            painter.fillRect(x - 8, y - fm.ascent() - 6, tw + 16, fm.height() + 12, QColor(0, 0, 0, 160))
            painter.setPen(QColor(255, 213, 0))
            painter.drawText(x, y, stars)

        if self._modification_badge:
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            fm = QFontMetrics(font)
            text = f"  {self._modification_badge}  "
            tw = fm.horizontalAdvance(text)
            x = 16
            y = 20 + fm.ascent()
            painter.fillRect(x, y - fm.ascent() - 4, tw + 8, fm.height() + 8, QColor(0, 0, 0, 180))
            painter.setPen(QColor(255, 213, 0))
            painter.drawText(x + 4, y, text)

    def paintEvent(self, event):
        if not self._pixmap_item.pixmap() or self._pixmap_item.pixmap().isNull():
            painter = QPainter(self.viewport())
            painter.fillRect(self.viewport().rect(), get_theme(True).get("canvas_bg", "#11111b"))
            font = QFont()
            font.setPointSize(14)
            painter.setFont(font)
            painter.setPen(QColor(150, 150, 150))
            text = "Open a folder to start sorting (Ctrl+O)"
            fm = QFontMetrics(font)
            tw = fm.horizontalAdvance(text)
            x = (self.width() - tw) // 2
            y = self.height() // 2
            painter.drawText(x, y, text)
            painter.end()
        else:
            super().paintEvent(event)
