🚀 Fast Image Sorter

A lightning-fast, keyboard-driven desktop application for culling and organizing massive photo collections. Built with Python and Tkinter, optimized for speed and stability.

✨ Key Features

Zero-Lag Workflow: Background threading ensures the UI never freezes, even when copying large RAW files.

Dark Mode UI: Professional dark theme to reduce eye strain and make photos pop.

Non-Destructive: Copies files to Keep or Discard folders, preserving your original source folder.

Instant Undo: Made a mistake? Press Ctrl+Z to instantly reverse the last action and delete the sorted copy.

EXIF Data HUD: View camera model, ISO, Aperture, and Date taken at a glance.

Visual Feedback: Anti-flicker rendering and instant visual overlays ("KEPT", "DISCARDED").

🎮 Controls

The app is designed to be used with one hand on the keyboard.

Action

Primary Key

Alternate Key

Keep Photo

Right Arrow ➡

K

Discard Photo

Down Arrow ⬇

N

Undo Last

Ctrl + Z



🛠️ How to Run (From Source)

Prerequisites

You need Python installed. This project relies on Pillow for image processing.

Installation

Clone or download this repository.

Install the required dependency:

pip install Pillow


Running the App

python sorter.py


📦 Building the EXE (Windows)

If you want to create a standalone .exe file to share with friends or run without Python:

Install PyInstaller:

pip install pyinstaller


Generate an Icon (Optional):
Ensure you have a valid .ico file named app.ico. You cannot simply rename a PNG; use a converter or a Python script to save it as format='ICO'.

Build Command:
Run this in your terminal:

pyinstaller --onefile --windowed --icon=app.ico sorter.py


Locate App:
Your sorter.exe will appear in the dist folder.

⚠️ Important Usage Notes

Background Queue: Because the app is multi-threaded, file copying happens in the background.

Do not close the app until the sidebar says "✔ All writes finished".

If you close it while it says "⚠ Writing X files...", the last few images may not be copied.

Windows Defender: When running the EXE for the first time, Windows may warn you ("Unknown Publisher"). This is normal for Python apps not signed with a paid certificate. Click More Info -> Run Anyway.

📝 License

Free to use and modify. Happy Sorting!
