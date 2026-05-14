from PySide6.QtGui import QPixmap


class ImageCache:
    def __init__(self, max_size=50):
        self._cache = {}
        self._max_size = max_size

    def get(self, path):
        return self._cache.get(path)

    def put(self, path, pixmap):
        if len(self._cache) >= self._max_size:
            self._evict_one()
        self._cache[path] = pixmap

    def remove(self, path):
        self._cache.pop(path, None)

    def clear(self):
        self._cache.clear()

    def _evict_one(self):
        if self._cache:
            self._cache.pop(next(iter(self._cache)))

    def contains(self, path):
        return path in self._cache

    def __contains__(self, path):
        return path in self._cache
