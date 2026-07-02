# -- Path bootstrap (works when run directly or via main.py) ------------------
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# -----------------------------------------------------------------------------
"""Theme loader — applies QSS stylesheets to the application."""

import os
from PyQt6.QtWidgets import QApplication


def apply_theme(app: QApplication, theme: str) -> None:
    """Apply the given theme ('moltin-dark' or 'moltin-light') to the app."""
    styles_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "styles")

    if theme == "moltin-light":
        qss_path = os.path.join(styles_dir, "light.qss")
    else:
        qss_path = os.path.join(styles_dir, "dark.qss")

    try:
        with open(qss_path, "r", encoding="utf-8") as f:
            stylesheet = f.read()
        app.setStyleSheet(stylesheet)
    except FileNotFoundError:
        print(f"[Theme] Stylesheet not found: {qss_path}")
