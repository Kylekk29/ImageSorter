import sys
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from turbo_sorter.core.config import ConfigManager, APP_NAME
from turbo_sorter.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("TurboSorter")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    app.setStyle("Fusion")

    config = ConfigManager()
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
