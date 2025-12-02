📸 Turbo Photo Sorter (v4.3)

A fast, persistent, and robust desktop application built with Python and Tkinter for quickly culling and sorting large batches of photographs. This tool allows photographers to rapidly categorize images into "Keep," "Discard," and "Maybe" folders, saving your progress automatically.

✨ Features

Non-Destructive Sorting: Uses shutil.move for lightning-fast file operations that preserve 100% of the original image quality and file metadata.

Session Persistence: Automatically creates a turbo_sorter_log.json file in the source folder to track processed files. If you close and restart the app, it resumes exactly where you left off.

Robust EXIF Display: Integrates the exifread library to provide reliable, detailed metadata (Camera model, Aperture, ISO, etc.) for informed culling decisions.

Auto-Orientation Fix: Correctly handles all EXIF orientation flags using ImageOps.exif_transpose, ensuring photos are displayed upright regardless of the camera's orientation.

Keyboard Shortcuts: Turbo-charge your workflow with dedicated shortcuts:

Keep: Right Arrow, K, or Space

Discard: Down Arrow or N

Maybe: M

Undo: Ctrl+Z

Dark/Light Theme: Includes a working theme toggle for comfortable use in any environment.

⚙️ Requirements

To run the application from source code, you need Python 3.x and the following libraries:

pip install pillow exifread


🚀 Usage

Run the script:

python sorter.py


Load a Folder: Click the "Click to Load Folder" area and select the directory containing the photos you wish to sort.

The application will automatically create three new subfolders in the source directory: Keep, Discard, and Maybe.

Start Sorting: Use the keyboard shortcuts (recommended) or the sidebar buttons to move the current image to the corresponding folder.

Persistence:

As you sort, the file names are logged in turbo_sorter_log.json inside your source folder.

If you close the app and reopen the same folder, only unsorted images will appear in the queue.

Undo: Press Ctrl+Z to reverse the last move action, placing the file back into the source folder and allowing you to re-sort it.

📦 Building an Executable (PyInstaller)

If you want to create a standalone application that does not require the user to install Python or the required libraries, follow these steps using PyInstaller.

Step 1: Install PyInstaller

pip install pyinstaller


Step 2: Build the Executable

Since this is a GUI application (Tkinter), you must use the --noconsole (or --windowed) flag to prevent a terminal window from opening alongside the GUI. The --onefile flag creates a single executable file.

Run this command from your terminal, located in the directory of your sorter.py script:

pyinstaller --onefile --noconsole --name "TurboSorter" sorter.py


Step 3: Find the Executable

After compilation, PyInstaller will create a few directories:

build/: Contains temporary build files.

__pycache__/: Python cache files.

dist/: This is where your final executable is located.

The finished executable (TurboSorter.exe on Windows, or TurboSorter on macOS/Linux) will be in the dist folder. You can distribute this file directly to users.
