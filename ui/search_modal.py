# -- Path bootstrap (works when run directly or via main.py) ------------------
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# -----------------------------------------------------------------------------
"""
Search Modal — full-text and quick-switcher search overlay.
Ctrl+P: quick title switcher
Ctrl+Shift+F: full text search with snippets
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QWidget,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QKeyEvent


class SearchModal(QDialog):
    note_selected = pyqtSignal(str)  # file path

    def __init__(self, search_service, mode: str = "quick", parent=None):
        """
        mode: 'quick' for title-only Ctrl+P, 'full' for Ctrl+Shift+F
        """
        super().__init__(parent)
        self.search_service = search_service
        self.mode = mode
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self._build_ui()

        # Debounce timer
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(150)
        self._debounce.timeout.connect(self._run_search)

        # Initial results
        self._run_search()

    def _build_ui(self):
        # Outer container (dark overlay)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setObjectName("search_modal")
        container.setFixedWidth(580)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Search input
        placeholder = "Jump to note…" if self.mode == "quick" else "Search notes…"
        self._input = QLineEdit()
        self._input.setObjectName("search_input")
        self._input.setPlaceholderText(placeholder)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._select_current)
        layout.addWidget(self._input)

        # Results count
        self._count_label = QLabel()
        self._count_label.setObjectName("ai_explanation_text")
        self._count_label.setContentsMargins(14, 6, 14, 2)
        layout.addWidget(self._count_label)

        # Results list
        self._list = QListWidget()
        self._list.setMaximumHeight(400)
        self._list.itemDoubleClicked.connect(self._on_item_selected)
        self._list.itemActivated.connect(self._on_item_selected)
        layout.addWidget(self._list)

        outer.addWidget(container, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        self.setMinimumHeight(500)
        self.resize(QApplication.primaryScreen().size().width(),
                    QApplication.primaryScreen().size().height())

    def showEvent(self, event):
        super().showEvent(event)
        self._input.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_Down:
            self._list.setFocus()
            if self._list.currentRow() < self._list.count() - 1:
                self._list.setCurrentRow(self._list.currentRow() + 1)
            self._input.setFocus()
        elif event.key() == Qt.Key.Key_Up:
            if self._list.currentRow() > 0:
                self._list.setCurrentRow(self._list.currentRow() - 1)
        else:
            super().keyPressEvent(event)

    def _on_text_changed(self, text: str):
        self._debounce.start()

    def _run_search(self):
        query = self._input.text()

        if self.mode == "quick":
            results = self.search_service.search_titles(query, limit=20)
        else:
            results = self.search_service.search(query, limit=30) if query.strip() else []

        self._list.clear()
        for r in results:
            item = QListWidgetItem()
            if self.mode == "quick":
                item.setText(f"📄  {r['name']}\n    {r['relativePath']}")
            else:
                snippet = r.get("snippet", "")
                item.setText(f"📄  {r['name']}\n    {snippet}")
            item.setData(Qt.ItemDataRole.UserRole, r["path"])
            self._list.addItem(item)

        count = len(results)
        self._count_label.setText(f"{count} result{'s' if count != 1 else ''}")

        if results:
            self._list.setCurrentRow(0)

    def _select_current(self):
        item = self._list.currentItem()
        if item:
            self._on_item_selected(item)
        elif self._list.count() > 0:
            self._on_item_selected(self._list.item(0))

    def _on_item_selected(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.note_selected.emit(path)
            self.accept()
