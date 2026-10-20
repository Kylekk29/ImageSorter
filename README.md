**English** | [简体中文](README.zh-CN.md)

# Turbo Photo Sorter

Fast, keyboard-driven photo triage for Windows. Flip through a folder, mark each photo **Keep**, **Discard** or **Maybe**, make quick brightness and contrast fixes, and get your sorted copies in subfolders. Your original files are never changed.

[![Release](https://img.shields.io/github/v/release/Kylekk29/ImageSorter)](https://github.com/Kylekk29/ImageSorter/releases/latest)

## Download

Get `TurboPhotoSorter-1.0.0-x64-Portable.exe` from the [latest release](https://github.com/Kylekk29/ImageSorter/releases/latest). It is a single file; nothing is installed. Windows SmartScreen may warn because the app is not code-signed: choose **More info → Run anyway**.

## Features

- Three-way sorting with undo (`Ctrl+Z`)
- Background loading and a thumbnail filmstrip for lag-free navigation
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
