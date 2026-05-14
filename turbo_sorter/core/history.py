from dataclasses import dataclass, field
from typing import List


@dataclass
class HistoryEntry:
    file_path: str
    action: str
    rating: int = 0
    label: str = ""
    from_folder: str = ""
    to_folder: str = ""
    description: str = ""


class HistoryManager:
    def __init__(self, max_history=200):
        self._entries: List[HistoryEntry] = []
        self._index = -1
        self._max = max_history

    def push(self, entry: HistoryEntry):
        self._entries = self._entries[: self._index + 1]
        self._entries.append(entry)
        if len(self._entries) > self._max:
            self._entries.pop(0)
        self._index = len(self._entries) - 1

    def can_undo(self):
        return self._index >= 0

    def can_redo(self):
        return self._index < len(self._entries) - 1

    def undo(self):
        if not self.can_undo():
            return None
        entry = self._entries[self._index]
        self._index -= 1
        return entry

    def redo(self):
        if not self.can_redo():
            return None
        self._index += 1
        return self._entries[self._index]

    def peek_last(self):
        if self._entries:
            return self._entries[-1]
        return None

    @property
    def count(self):
        return len(self._entries)

    def clear(self):
        self._entries.clear()
        self._index = -1
