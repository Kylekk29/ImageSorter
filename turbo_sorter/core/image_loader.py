import os
import threading
from queue import Queue, Empty

from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtGui import QPixmap, QImage
from PIL import Image, ImageEnhance, ImageOps
import exifread


class ImageLoadRequest:
    def __init__(self, path, quality=95):
        self.path = path
        self.quality = quality


class ImageLoadResult:
    def __init__(self, path, pixmap=None, exif=None, error=None, pil_image=None):
        self.path = path
        self.pixmap = pixmap
        self.exif = exif or {}
        self.error = error
        self.pil_image = pil_image


class ImageProcessor:
    @staticmethod
    def load_pil_image(path):
        try:
            img = Image.open(path)
            img = ImageOps.exif_transpose(img)
            return img.convert("RGB")
        except Exception as e:
            return None

    @staticmethod
    def pil_to_pixmap(pil_image):
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        data = pil_image.tobytes("raw", "RGB")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format_RGB888)
        return QPixmap.fromImage(qimage)

    @staticmethod
    def read_exif(path):
        exif_data = {}
        try:
            with open(path, "rb") as f:
                tags = exifread.process_file(f, details=False)
            tag_map = {
                "Image Make": "Camera",
                "Image Model": "Model",
                "EXIF DateTimeOriginal": "Date",
                "EXIF ExposureTime": "Shutter",
                "EXIF FNumber": "Aperture",
                "EXIF ISOSpeedRatings": "ISO",
                "EXIF FocalLength": "Focal Length",
                "EXIF LensModel": "Lens",
                "EXIF Flash": "Flash",
                "EXIF ExposureProgram": "Program",
                "EXIF ExposureBiasValue": "Exposure Bias",
            }
            for exif_key, label in tag_map.items():
                if exif_key in tags:
                    val = str(tags[exif_key])
                    exif_data[label] = val
        except Exception:
            pass
        return exif_data

    @staticmethod
    def adjust_image(pil_image, brightness=1.0, contrast=1.0, rotation=0):
        img = pil_image
        if rotation:
            img = img.rotate(rotation, expand=True, resample=Image.BICUBIC)
        if brightness != 1.0:
            img = ImageEnhance.Brightness(img).enhance(brightness)
        if contrast != 1.0:
            img = ImageEnhance.Contrast(img).enhance(contrast)
        return img

    @staticmethod
    def auto_adjust(pil_image):
        img = ImageOps.autocontrast(pil_image, cutoff=5)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.05)
        return img

    @staticmethod
    def crop_to_aspect(pil_image, width_ratio, height_ratio):
        w, h = pil_image.size
        target_ratio = width_ratio / height_ratio
        current_ratio = w / h
        if current_ratio > target_ratio:
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            return pil_image.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            return pil_image.crop((0, top, w, top + new_h))


class ImageLoaderWorker(QObject):
    finished = Signal(ImageLoadResult)
    progress = Signal(str)

    def __init__(self):
        super().__init__()
        self._queue = Queue()
        self._running = True
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._queue.put(None)

    def enqueue(self, request):
        self._queue.put(request)

    def clear_queue(self):
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Empty:
                break

    def _worker_loop(self):
        while self._running:
            try:
                request = self._queue.get(timeout=0.5)
            except Empty:
                continue
            if request is None:
                break
            try:
                exif = ImageProcessor.read_exif(request.path)
                pil_image = ImageProcessor.load_pil_image(request.path)
                if pil_image is None:
                    self.finished.emit(ImageLoadResult(request.path, error="Failed to load image"))
                    continue
                pixmap = ImageProcessor.pil_to_pixmap(pil_image)
                result = ImageLoadResult(
                    path=request.path,
                    pixmap=pixmap,
                    exif=exif,
                    pil_image=pil_image,
                )
                self.finished.emit(result)
            except Exception as e:
                self.finished.emit(ImageLoadResult(request.path, error=str(e)))


class ThumbnailLoader(QObject):
    finished = Signal(str, QPixmap)

    def __init__(self, size=(120, 80)):
        super().__init__()
        self._size = size
        self._queue = Queue()
        self._running = True
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._thumb_worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._queue.put(None)

    def enqueue(self, path):
        self._queue.put(path)

    def clear_queue(self):
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Empty:
                break

    def _thumb_worker(self):
        while self._running:
            try:
                path = self._queue.get(timeout=0.5)
            except Empty:
                continue
            if path is None:
                break
            try:
                pil_image = ImageProcessor.load_pil_image(path)
                if pil_image is None:
                    continue
                pil_image.thumbnail(self._size, Image.LANCZOS)
                pixmap = ImageProcessor.pil_to_pixmap(pil_image)
                self.finished.emit(path, pixmap)
            except Exception:
                pass
