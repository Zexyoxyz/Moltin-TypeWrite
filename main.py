"""
Moltin TypeWriter — Main entry point.
A modern knowledge management application with deeply integrated AI writing assistance.
"""

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from ui.main_window import MainWindow
from config.settings import SettingsManager
from config.app_dirs import ensure_app_dirs


def main():
    # High-DPI is enabled by default in Qt6 — no attribute needed

    app = QApplication(sys.argv)
    app.setApplicationName("Moltin TypeWriter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Moltin")

    # Set app icon
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Bootstrap AppData folders
    ensure_app_dirs()

    # Load settings
    settings = SettingsManager()

    # Apply initial theme
    from ui.theme import apply_theme
    apply_theme(app, settings.get("theme", "moltin-dark"))

    # Launch main window
    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
