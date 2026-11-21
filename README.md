**English** | [简体中文](README.zh-CN.md)

# Turbo Photo Sorter

Turbo Photo Sorter is an open-source Windows app for reviewing photos with the keyboard. Mark each shot **Keep**, **Discard**, or **Maybe**. The app puts copies in category folders and keeps your originals intact.

## Download for Windows x64

[Download TurboPhotoSorter-1.1.0-x64-Portable.exe](https://github.com/Kylekk29/ImageSorter/releases/download/v1.1.0/TurboPhotoSorter-1.1.0-x64-Portable.exe) and double-click it. The portable app runs without an installer.

The executable is unsigned, so Windows SmartScreen may show a prompt. The [release page](https://github.com/Kylekk29/ImageSorter/releases/latest) includes its SHA-256 checksum.

## Review photos

1. Drop a folder or select photos from one folder and drop them onto the preview. You can also open a folder with `Ctrl+O`.
2. Press `K` to keep, `N` to discard, or `M` to mark a photo as maybe. After saving, the app advances to the next unreviewed photo.
3. Use `[` and `]` or click a thumbnail to browse. Press `Ctrl+Z` to undo the last decision in the current session and remove its output copies.

The app supports JPEG, PNG, TIFF, WebP, and BMP. The filmstrip loads thumbnails as you browse. Use the sidebar for brightness, contrast, EXIF details, and light or dark mode.

| Shortcut | Action |
| --- | --- |
| `K`, `→`, or `Space` | Keep |
| `N` or `↓` | Discard |
| `M` | Maybe |
| `[` / `]` | Browse left or right |
| `Ctrl+Z` | Undo |
| `Ctrl+O` | Open a folder |
| `F11` / `Esc` | Enter or leave fullscreen |
| Mouse wheel or `+` / `-` | Zoom |
| `0` | Reset zoom |
| Middle or right mouse drag | Pan the zoomed preview |

## Where the files go

The source folder holds the output.

- `Keep/`, `Discard/`, and `Maybe/` contain copies of the originals.
- `Keep_Modified/`, `Discard_Modified/`, and `Maybe_Modified/` contain full-resolution copies with your brightness and contrast changes.
- `turbo_sorter_log.json` records completed decisions so you can resume when you reopen the folder.

The app updates progress after saving the requested copies. If a destination already contains a file with the same name, the app reports the conflict and preserves the existing file.

## Run or build from source

Use Python 3.10 or later with Tkinter. To produce the Windows x64 executable, use 64-bit x86 Python on Windows.

```powershell
python -m pip install -r requirements.txt
python main.py
```

Build the portable executable into `dist/` with PowerShell.

```powershell
.\build.ps1
```

Run the regression tests with `python -m unittest discover -s tests -v`.

## Open source

The project's source code is available under the [MIT License](LICENSE). The portable executable includes the project's license and bundled dependency notices.
