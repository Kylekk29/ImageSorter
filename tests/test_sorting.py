import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from sorting import LOG_FILE_NAME, load_progress, save_decision, undo_decision


class SortingTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.source = self.folder / "photo.jpg"
        self.source.write_bytes(b"original")

    def test_decision_and_undo_preserve_original_and_legacy_progress(self):
        (self.folder / LOG_FILE_NAME).write_text(
            json.dumps({"processed_files": ["earlier.jpg"]}), encoding="utf-8"
        )
        processed = load_progress(self.folder)
        outputs = save_decision(self.folder, self.source.name, "Keep", processed,
                                lambda source, output: output.write(b"adjusted"))
        self.assertEqual([path.read_bytes() for path in outputs], [b"original", b"adjusted"])
        self.assertEqual(load_progress(self.folder), {"earlier.jpg", self.source.name})

        undo_decision(self.folder, self.source.name, outputs, load_progress(self.folder))

        self.assertTrue(all(not path.exists() for path in outputs))
        self.assertEqual(self.source.read_bytes(), b"original")
        self.assertEqual(load_progress(self.folder), {"earlier.jpg"})

    def test_adjusted_collision_does_not_overwrite_or_advance(self):
        destination = self.folder / "Keep_Modified" / self.source.name
        destination.parent.mkdir()
        destination.write_bytes(b"existing")

        with self.assertRaises(FileExistsError):
            save_decision(self.folder, self.source.name, "Keep", set(),
                          lambda source, output: output.write(b"adjusted"))

        self.assertEqual(destination.read_bytes(), b"existing")
        self.assertFalse((self.folder / "Keep" / self.source.name).exists())
        self.assertEqual(load_progress(self.folder), set())

    def test_failed_progress_write_rolls_back_sort_and_undo(self):
        with patch("sorting.os.replace", side_effect=PermissionError("log locked")):
            with self.assertRaises(PermissionError):
                save_decision(self.folder, self.source.name, "Keep", set())
        self.assertFalse((self.folder / "Keep" / self.source.name).exists())
        self.assertEqual(load_progress(self.folder), set())

        outputs = save_decision(self.folder, self.source.name, "Keep", set())
        with patch("sorting.os.replace", side_effect=PermissionError("log locked")):
            with self.assertRaises(PermissionError):
                undo_decision(self.folder, self.source.name, outputs, load_progress(self.folder))
        self.assertEqual(outputs[0].read_bytes(), b"original")
        self.assertEqual(load_progress(self.folder), {self.source.name})


if __name__ == "__main__":
    unittest.main()
