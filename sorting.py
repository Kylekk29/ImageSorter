import json
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp


LOG_FILE_NAME = "turbo_sorter_log.json"


def load_progress(folder):
    try:
        with (folder / LOG_FILE_NAME).open(encoding="utf-8") as log:
            data = json.load(log)
    except FileNotFoundError:
        return set()
    files = data.get("processed_files") if isinstance(data, dict) else None
    if not isinstance(files, list) or not all(isinstance(name, str) for name in files):
        raise ValueError("Invalid sorting progress log")
    return set(files)


def save_progress(folder, files):
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder, delete=False) as log:
            temporary = Path(log.name)
            json.dump({"processed_files": sorted(files)}, log)
        os.replace(temporary, folder / LOG_FILE_NAME)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_decision(folder, filename, action, processed, save_adjusted=None):
    source = folder / filename
    destination = folder / action / filename
    created = []
    try:
        destination.parent.mkdir(exist_ok=True)
        with source.open("rb") as original, destination.open("xb") as copy:
            created.append(destination)
            shutil.copyfileobj(original, copy)
        shutil.copystat(source, destination)
        if save_adjusted is not None:
            adjusted = folder / f"{action}_Modified" / filename
            adjusted.parent.mkdir(exist_ok=True)
            with adjusted.open("xb") as output:
                created.append(adjusted)
                save_adjusted(source, output)
        save_progress(folder, processed | {filename})
    except Exception:
        for path in reversed(created):
            # copy metadata can include a Windows read-only attribute.
            path.chmod(0o600)
            path.unlink(missing_ok=True)
        raise
    return created


def undo_decision(folder, filename, outputs, processed):
    staging = Path(mkdtemp(prefix=".turbo-undo-", dir=folder))
    moved = []
    try:
        for index, output in enumerate(outputs):
            staged = staging / str(index)
            try:
                output.rename(staged)
            except FileNotFoundError:
                continue
            moved.append((staged, output))
        save_progress(folder, processed - {filename})
    except Exception:
        for staged, output in reversed(moved):
            staged.rename(output)
        staging.rmdir()
        raise
    try:
        for staged, _ in moved:
            staged.chmod(0o600)
            staged.unlink()
        staging.rmdir()
    except OSError as error:
        return error
