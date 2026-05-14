# Turbo Photo Sorter

A professional photo sorting and editing application built with Python and **PySide6** (Qt). Designed for photographers who need to rapidly browse, rate, and organize large collections of images.

[![GitHub](https://img.shields.io/badge/GitHub-ImageSorter-181717?logo=github)](https://github.com/Kylekk29/ImageSorter)

## Features

### Core Sorting
- **3-Way Sorting**: Keep / Discard / Maybe with keyboard shortcuts
- **Undo/Redo**: Full history tracking (`Ctrl+Z` / `Ctrl+Y`)
- **Smart Prefetching**: Background image loading for zero-lag navigation
- **Session Recovery**: Auto-saves processed files to prevent re-processing

### Image Editing
- **Brightness & Contrast**: Real-time slider adjustments with 40ms debounce for smooth performance
- **Rotation**: 90° left/right with high-quality bicubic resampling
- **Auto-Adjust**: One-click auto contrast + brightness bump
- **Crop Presets**: Square (1:1), HD (16:9), Standard (4:3), Classic (3:2), Ultrawide (21:9)
- **Zoom & Pan**: Mouse wheel zoom (0.05x-20x), click-and-drag pan when zoomed in

### Professional Tools
- **Star Rating**: Rate images 1-5 stars (click or press 1-5)
- **Color Labels**: Red, Yellow, Green, Blue, Purple
- **EXIF Metadata**: Camera make/model, date, lens, ISO, aperture, shutter speed
- **Comparison View**: Quick compare mode between consecutive images
- **Fullscreen Mode**: Immersive fullscreen with overlay hints
- **Slideshow**: Auto-advancing with loop, shuffle, and configurable delay

### Organization
- **Thumbnail Filmstrip**: Horizontal scrollable strip with lazy-loaded thumbnails
- **Search & Filter**: Real-time filename filtering (`Ctrl+F`)
- **Batch Rename**: Pattern-based renaming using `{n}` placeholder
- **Batch Export**: Copy remaining images to a destination folder
- **Statistics Export**: Generate text report of sorting activity

### Customization
- **Dark/Light Themes**: Toggle between Catppuccin-inspired dark and light color schemes
- **Customizable Shortcuts**: Configurable key bindings in `turbo_sorter_config.json`
- **Persistent Settings**: Window geometry, splitter sizes, last directory remembered

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `→` / `Space` / `K` | Keep |
| `↓` / `N` | Discard |
| `M` | Maybe |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `R` | Rotate Right |
| `L` | Rotate Left |
| `A` | Auto Adjust |
| `F` | Fullscreen |
| `S` | Slideshow |
| `C` | Compare Mode |
| `1`-`5` | Star Rating (press again to clear) |
| `+` / `-` | Zoom In / Zoom Out |
| `0` | Reset View |
| `Ctrl+F` | Search / Filter |
| `Ctrl+O` | Open Folder |
| `Ctrl+Q` | Quit |
| `Esc` | Exit fullscreen / slideshow |
| `◀` / `▶` | Previous / Next image |

## Installation

### Requirements
- Python 3.10+
- PySide6
- Pillow
- exifread

### Quick Start
```bash
# Clone the repository
git clone https://github.com/Kylekk29/ImageSorter.git
cd ImageSorter

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
# Or:
python -m turbo_sorter
```

## Building an Executable

Build a standalone Windows executable with PyInstaller:

```powershell
# Install PyInstaller (included in requirements.txt)
pip install pyinstaller

# Method 1: One-command build
pyinstaller --name "TurboPhotoSorter" --windowed --onefile `
  --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui `
  --hidden-import PySide6.QtWidgets main.py

# Method 2: Using the spec file
pyinstaller build.spec
```

Output: `dist/TurboPhotoSorter.exe`

## Folder Structure

When you load an image folder, the app creates:

```
YourImages/
├── Keep/               # Copied images marked Keep
├── Discard/            # Copied images marked Discard
├── Maybe/              # Copied images marked Maybe
├── Keep_Modified/      # Edited keeps (adjustments baked in)
├── Discard_Modified/   # Edited discards
├── Maybe_Modified/     # Edited maybes
├── turbo_sorter_log.json
└── turbo_sorter_statistics.txt
```

## Project Structure

```
turbo_sorter/
├── __init__.py          # Package version
├── __main__.py          # `python -m` entry
├── app.py               # QApplication setup
├── main_window.py       # Main window, menus, signals, shortcuts
├── dialogs.py           # Settings, Batch, About dialogs
├── core/
│   ├── config.py        # ConfigManager (JSON persistence)
│   ├── image_cache.py   # LRU pixmap cache
│   ├── image_loader.py  # Background threaded image loading (PIL + EXIF)
│   ├── history.py       # Undo/redo history manager
│   ├── session.py       # Session logging & recovery
│   └── sorter.py        # File operations (Keep/Discard/Maybe)
├── widgets/
│   ├── image_view.py    # Zoomable QGraphicsView with overlay painting
│   ├── filmstrip.py     # Thumbnail filmstrip (QListWidget)
│   └── info_panel.py    # Sidebar with EXIF, adjustments, rating, labels
└── theme/
    └── styles.py        # Dark/Light QSS stylesheets
```

## Configuration

Edit `turbo_sorter_config.json` in the working directory:

```json
{
  "dark": true,
  "slideshow_delay": 3,
  "image_quality": 95,
  "prefetch_count": 3,
  "max_history": 200,
  "last_directory": "C:/Photos",
  "window_geometry": "1400x900",
  "slideshow_loop": true,
  "slideshow_shuffle": false
}
```

## License

MIT

---

Built with Python, PySide6, and Pillow.
