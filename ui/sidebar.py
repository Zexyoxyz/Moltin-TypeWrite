# ── Path bootstrap ────────────────────────────────────────────────────────────
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# ─────────────────────────────────────────────────────────────────────────────

"""
Sidebar — redesigned clean file explorer, backlinks panel, and tags panel.
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog,
    QMessageBox, QTabWidget, QListWidget, QListWidgetItem,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QAction, QFont


class FileExplorer(QWidget):
    file_opened = pyqtSignal(str)
    file_created = pyqtSignal(str)
    new_note_requested = pyqtSignal()
    file_deleted = pyqtSignal(str)
    file_renamed = pyqtSignal(str, str)
    folder_created = pyqtSignal(str)

    def __init__(self, file_service, parent=None):
        super().__init__(parent)
        self.file_service = file_service
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Section header
        header = QWidget()
        header.setObjectName("sidebar_section_header")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(14, 6, 8, 6)

        lbl = QLabel("FILES")
        lbl.setObjectName("sidebar_section_label")

        h_lay.addWidget(lbl)
        h_lay.addStretch()
        layout.addWidget(header)

        # File tree
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(14)
        self._tree.setAnimated(True)
        self._tree.setUniformRowHeights(True)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_menu)
        layout.addWidget(self._tree, 1)

    def refresh(self, tree_data: list[dict]) -> None:
        self._tree.clear()
        self._populate(tree_data, self._tree.invisibleRootItem())

    def _populate(self, nodes: list[dict], parent: QTreeWidgetItem) -> None:
        for node in nodes:
            item = QTreeWidgetItem(parent)
            is_folder = node["type"] == "folder"
            # Clean minimal labels — folder icon via text prefix
            prefix = "▸  " if is_folder else "    "
            item.setText(0, prefix + node["name"])
            item.setData(0, Qt.ItemDataRole.UserRole, node["path"])
            item.setData(0, Qt.ItemDataRole.UserRole + 1, node["type"])
            if is_folder and node.get("children"):
                self._populate(node["children"], item)
                item.setExpanded(True)

    def _on_double_click(self, item: QTreeWidgetItem, _col):
        if item.data(0, Qt.ItemDataRole.UserRole + 1) == "file":
            self.file_opened.emit(item.data(0, Qt.ItemDataRole.UserRole))

    def _show_menu(self, pos: QPoint):
        item = self._tree.itemAt(pos)
        menu = QMenu(self)
        if item:
            path = item.data(0, Qt.ItemDataRole.UserRole)
            node_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if node_type == "file":
                menu.addAction(QAction("Open", self, triggered=lambda: self.file_opened.emit(path)))
            menu.addAction(QAction("Rename…", self, triggered=lambda: self._rename(path, node_type)))
            menu.addSeparator()
            menu.addAction(QAction("Delete", self, triggered=lambda: self._delete(path, node_type)))
        else:
            menu.addAction(QAction("New Note…", self, triggered=self.new_note_requested.emit))
            menu.addAction(QAction("New Folder…", self, triggered=self._create_folder))
        menu.exec(self._tree.mapToGlobal(pos))

    def _rename(self, path: str, node_type: str):
        current = Path(path).stem if node_type == "file" else Path(path).name
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=current)
        if ok and name.strip():
            new_path = self.file_service.rename_note(path, name.strip())
            self.file_renamed.emit(path, new_path)

    def _delete(self, path: str, node_type: str):
        name = Path(path).name
        reply = QMessageBox.question(
            self, "Delete", f"Delete '{name}'?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes and node_type == "file":
            self.file_service.delete_note(path)
            self.file_deleted.emit(path)

    def _create_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            p = self.file_service.create_folder(name.strip())
            self.folder_created.emit(p)


class BacklinksPanel(QWidget):
    link_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("sidebar_section_header")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(14, 6, 8, 6)
        lbl = QLabel("BACKLINKS")
        lbl.setObjectName("sidebar_section_label")
        self._count = QLabel("0")
        self._count.setObjectName("ai_provider_badge")
        h_lay.addWidget(lbl)
        h_lay.addStretch()
        h_lay.addWidget(self._count)
        layout.addWidget(header)

        self._context_lbl = QLabel("Open a note to see backlinks")
        self._context_lbl.setObjectName("ai_explanation_text")
        self._context_lbl.setWordWrap(True)
        self._context_lbl.setContentsMargins(14, 8, 14, 4)
        layout.addWidget(self._context_lbl)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(
            lambda item: self.link_clicked.emit(item.data(Qt.ItemDataRole.UserRole))
        )
        layout.addWidget(self._list, 1)

    def set_backlinks(self, note_name: str, backlinks: list[dict]):
        self._list.clear()
        self._context_lbl.setText(f"↩  {note_name}")
        self._count.setText(str(len(backlinks)))
        for bl in backlinks:
            item = QListWidgetItem()
            ctx = bl.get("context", "")[:55]
            item.setText(f"{bl['sourceName']}\n    {ctx}")
            item.setData(Qt.ItemDataRole.UserRole, bl["sourcePath"])
            item.setToolTip(bl.get("context", ""))
            self._list.addItem(item)


class TagsPanel(QWidget):
    tag_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("sidebar_section_header")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(14, 6, 8, 6)
        lbl = QLabel("TAGS")
        lbl.setObjectName("sidebar_section_label")
        h_lay.addWidget(lbl)
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.itemClicked.connect(
            lambda item: self.tag_clicked.emit(item.data(Qt.ItemDataRole.UserRole))
        )
        layout.addWidget(self._list, 1)

    def set_tags(self, tag_counts: dict[str, int]):
        self._list.clear()
        for tag, count in sorted(tag_counts.items()):
            item = QListWidgetItem(f"#  {tag}  ·  {count}")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self._list.addItem(item)


class Sidebar(QWidget):
    """Main sidebar — vault info + tabs for Files / Backlinks / Tags."""

    file_opened = pyqtSignal(str)
    file_created = pyqtSignal(str)
    file_deleted = pyqtSignal(str)
    file_renamed = pyqtSignal(str, str)
    new_note_requested = pyqtSignal()
    backlink_clicked = pyqtSignal(str)
    tag_clicked = pyqtSignal(str)

    def __init__(self, file_service, parent=None):
        super().__init__(parent)
        self.file_service = file_service
        self.setObjectName("sidebar")
        self.setMinimumWidth(200)
        self.setMaximumWidth(380)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Vault identity bar ───────────────────────────────────────────────
        self._vault_bar = QWidget()
        self._vault_bar.setObjectName("sidebar_vault_bar")
        vb_layout = QVBoxLayout(self._vault_bar)
        vb_layout.setContentsMargins(14, 10, 14, 10)
        vb_layout.setSpacing(2)

        self._vault_name_lbl = QLabel("No vault open")
        self._vault_name_lbl.setObjectName("sidebar_vault_name")

        vb_layout.addWidget(self._vault_name_lbl)
        
        # Huge New Note button
        self._new_note_btn = QPushButton("New Note")
        self._new_note_btn.setObjectName("btn_primary")
        self._new_note_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_note_btn.clicked.connect(self.new_note_requested.emit)
        vb_layout.addWidget(self._new_note_btn)
        
        layout.addWidget(self._vault_bar)

        # ── Tabbed panels ────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.South)
        self._tabs.setDocumentMode(True)

        self._explorer = FileExplorer(self.file_service)
        self._backlinks = BacklinksPanel()
        self._tags = TagsPanel()

        self._tabs.addTab(self._explorer, "Files")
        self._tabs.addTab(self._tags, "Tags")

        layout.addWidget(self._tabs, 1)

        # Wire signals
        self._explorer.file_opened.connect(self.file_opened)
        self._explorer.file_created.connect(self.file_created)
        self._explorer.file_deleted.connect(self.file_deleted)
        self._explorer.file_renamed.connect(self.file_renamed)
        self._backlinks.link_clicked.connect(self.backlink_clicked)
        self._tags.tag_clicked.connect(self.tag_clicked)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_vault(self, vault_path: str, vault_name: str):
        self._vault_name_lbl.setText(f"⬡  {vault_name}")

    def refresh_files(self, tree_data: list[dict]):
        self._explorer.refresh(tree_data)

    def set_backlinks(self, note_name: str, backlinks: list[dict]):
        self._backlinks.set_backlinks(note_name, backlinks)

    def set_tags(self, tag_counts: dict[str, int]):
        self._tags.set_tags(tag_counts)

    def show_backlinks_tab(self):
        self._tabs.setCurrentWidget(self._backlinks)
