**English** | [简体中文](README.zh-CN.md)

# Turbo Photo Sorter

Fast, keyboard-driven photo triage for Windows. Flip through a folder, mark each photo **Keep**, **Discard** or **Maybe**, make quick brightness and contrast fixes, and get your sorted copies in subfolders. Your original files are never changed.

[![Release](https://img.shields.io/github/v/release/Kylekk29/ImageSorter)](https://github.com/Kylekk29/ImageSorter/releases/latest)

## Download

Get `TurboPhotoSorter-1.0.0-x64-Portable.exe` from the [latest release](https://github.com/Kylekk29/ImageSorter/releases/latest). It is a single file; nothing is installed. Windows SmartScreen may warn because the app is not code-signed: choose **More info → Run anyway**.

## Features

- Drop a folder or selected photos from one folder onto the window. When you drop files, the review queue contains only those files.
- Three-way sorting with auto-advance. `Ctrl+Z` restores the last decision in the current session and removes its output copies.
- Browse without sorting using `[` and `]`, or click a thumbnail. The filmstrip shows a checkmark on photos reviewed during the session.
- Background preview loading and on-demand filmstrip thumbnails
- Non-destructive brightness and contrast, zoom and pan, fullscreen
- EXIF panel (camera, lens, exposure)
- Dark and light themes
- Progress is saved per folder, so you can quit and resume without re-sorting

## Keyboard shortcuts

| Key | Action |
|---|---|
| `→` / `K` / `Space` | Keep |
| `↓` / `N` | Discard |
| `M` | Maybe |
| `[` / `]` | Browse to previous / next photo without sorting |
| `Ctrl+Z` | Undo |
| `Ctrl+O` | Open folder |
| `F11` | Fullscreen (`Esc` exits) |
| `+` / `-` / `0` | Zoom in / out / reset |
| Mouse wheel | Zoom |
| Middle or right drag | Pan |

## Output

Sorting copies files into your source folder:

```
YourPhotos/
├── Keep/  Discard/  Maybe/                      # copies of the originals
├── Keep_Modified/  Discard_Modified/  Maybe_Modified/   # copies with your adjustments baked in
└── turbo_sorter_log.json                        # which files are done (enables resume)
```

Progress advances after the requested copies and the progress log are saved. If the destination filename already exists, the app keeps that file and reports the collision.

## Run from source

Python 3.10+ with Tkinter (included in the standard Windows installer).

```bash
pip install -r requirements.txt
python main.py
```

`requirements.txt` also lists PyInstaller, which is only needed to build the exe.

## Build the exe

```bash
pyinstaller --name TurboPhotoSorter --windowed --onefile --exclude-module PySide6 main.py
```

## License

MIT, see [LICENSE](LICENSE).
