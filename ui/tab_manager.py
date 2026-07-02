# -- Path bootstrap (works when run directly or via main.py) ------------------
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# -----------------------------------------------------------------------------
"""
TabManager — manages multiple open notes as tabs above the editor.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QScrollArea,
    QSizePolicy, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from config.settings import SettingsManager
from services.file_service import FileService


class TabButton(QPushButton):
    """Individual tab button with close button."""
    close_requested = pyqtSignal()
    tab_clicked = pyqtSignal()

    def __init__(self, name: str, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self._name = name
        self._is_dirty = False
        self._is_active = False
        self._update_text()
        self.setProperty("class", "tab_button")
        self.clicked.connect(self.tab_clicked.emit)

    def set_active(self, active: bool):
        self._is_active = active
        if active:
            self.setProperty("class", "tab_button_active")
        else:
            self.setProperty("class", "tab_button")
        # Force style refresh
        self.style().unpolish(self)
        self.style().polish(self)

    def set_dirty(self, dirty: bool):
        self._is_dirty = dirty
        self._update_text()

    def set_name(self, name: str):
        self._name = name
        self._update_text()

    def _update_text(self):
        prefix = "● " if self._is_dirty else ""
        self.setText(f"{prefix}{self._name}  ×")


class _TabBarWidget(QWidget):
    """QWidget subclass that carries the tab bar signals."""
    tab_changed = pyqtSignal(str)
    tab_closed = pyqtSignal(str)


class TabManager:
    """Manages tabs and synchronises with the editor."""

    def __init__(self, file_service: FileService, settings: SettingsManager):
        self.file_service = file_service
        self.settings = settings
        self._tabs: dict[str, TabButton] = {}  # path → TabButton
        self._active_path: str | None = None

        self.tab_bar_widget, self._tabs_layout = self._build_widget()
        # Expose signals
        self.tab_changed = self.tab_bar_widget.tab_changed
        self.tab_closed = self.tab_bar_widget.tab_closed

    def _build_widget(self) -> tuple["_TabBarWidget", QHBoxLayout]:
        bar = _TabBarWidget()
        bar.setObjectName("tab_bar")
        bar.setFixedHeight(38)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)  # type: ignore
        scroll.setFixedHeight(38)

        tabs_container = QWidget()
        tabs_container.setObjectName("tab_bar")
        tabs_layout = QHBoxLayout(tabs_container)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(0)
        tabs_layout.addStretch()

        scroll.setWidget(tabs_container)

        outer = QHBoxLayout(bar)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll)

        return bar, tabs_layout

    def open_tab(self, path: str, name: str, content: str):
        if path in self._tabs:
            self._set_active(path)
            return

        btn = TabButton(name, path)
        btn.tab_clicked.connect(lambda p=path: self._set_active(p))

        # Insert before the stretch
        count = self._tabs_layout.count()
        self._tabs_layout.insertWidget(count - 1, btn)
        self._tabs[path] = btn
        self._set_active(path)

    def _set_active(self, path: str):
        for p, btn in self._tabs.items():
            btn.set_active(p == path)
        self._active_path = path
        self.tab_changed.emit(path)

    def close_tab_by_path(self, path: str):
        if path not in self._tabs:
            return
        btn = self._tabs.pop(path)
        self._tabs_layout.removeWidget(btn)
        btn.deleteLater()
        self.tab_closed.emit(path)

        # Switch to another tab
        if self._active_path == path and self._tabs:
            self._set_active(list(self._tabs.keys())[-1])

    def mark_clean(self, path: str):
        if path in self._tabs:
            self._tabs[path].set_dirty(False)

    def mark_dirty(self, path: str):
        if path in self._tabs:
            self._tabs[path].set_dirty(True)

    def rename_tab(self, old_path: str, new_path: str, new_name: str):
        if old_path not in self._tabs:
            return
        btn = self._tabs.pop(old_path)
        btn.path = new_path
        btn.set_name(new_name)
        self._tabs[new_path] = btn
        if self._active_path == old_path:
            self._active_path = new_path

    def get_open_paths(self) -> list[str]:
        return list(self._tabs.keys())

    def next_tab(self):
        paths = list(self._tabs.keys())
        if not paths or self._active_path not in paths:
            return
        idx = (paths.index(self._active_path) + 1) % len(paths)
        self._set_active(paths[idx])

    def prev_tab(self):
        paths = list(self._tabs.keys())
        if not paths or self._active_path not in paths:
            return
        idx = (paths.index(self._active_path) - 1) % len(paths)
        self._set_active(paths[idx])
