"""
MainWindow — the application's primary window.
Orchestrates: sidebar, tab bar, editor, AI panel, menus, and keyboard shortcuts.
"""

# ── Path bootstrap (works when run directly or via main.py) ──────────────────
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# ─────────────────────────────────────────────────────────────────────────────

import os
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QLabel, QStatusBar, QToolBar, QPushButton,
    QMenuBar, QMenu, QFileDialog, QInputDialog, QMessageBox,
    QTabBar, QTabWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QFont

from config.settings import SettingsManager
from services.file_service import FileService
from services.search_service import SearchService
from services.backlink_service import BacklinkService
from services.ai.ai_manager import AIManager
from config.app_dirs import get_vaults_dir

from ui.editor import MarkdownEditor
from ui.sidebar import Sidebar
from ui.ai_panel import AIPanel
from ui.search_modal import SearchModal
from ui.settings_dialog import SettingsDialog
from ui.tab_manager import TabManager
from ui.theme import apply_theme


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsManager):
        super().__init__()
        self.settings = settings

        # ── Services ──────────────────────────────────────────────────────────
        self.file_service = FileService()
        self.search_service = SearchService(self.file_service)
        self.backlink_service = BacklinkService(self.file_service)
        self.ai_manager = AIManager(self.settings)

        # ── State ─────────────────────────────────────────────────────────────
        self._current_vault_path: str | None = None
        self._current_note_path: str | None = None

        # ── Window setup ──────────────────────────────────────────────────────
        self.setWindowTitle("Moltin TypeWriter")
        self.resize(
            settings.get("window_width", 1400),
            settings.get("window_height", 900),
        )
        if settings.get("window_maximized", False):
            self.showMaximized()

        self._build_ui()
        self._build_menus()
        self._build_shortcuts()
        self._build_status_bar()

        # ── Auto-open last vault ───────────────────────────────────────────────
        last_vault = settings.get("current_vault_path")
        if last_vault and os.path.isdir(last_vault):
            QTimer.singleShot(100, lambda: self._open_vault(last_vault))
        else:
            # Open the default example vault
            default_vault = str(get_vaults_dir() / "My Notes")
            if os.path.isdir(default_vault):
                QTimer.singleShot(100, lambda: self._open_vault(default_vault))

        # ── Initial API Key Prompt ────────────────────────────────────────────
        if not self.settings.get("encrypted_keys", {}):
            QTimer.singleShot(500, self._prompt_initial_api_key)

    def _prompt_initial_api_key(self):
        QMessageBox.information(
            self,
            "Welcome to Moltin TypeWriter",
            "To use the AI features (like grammar checking, rephrasing, and brainstorming), "
            "you need to provide your own API key.\n\n"
            "Please add your API key in the Settings dialog that will open now."
        )
        self._open_settings()

    # ─── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Tab Manager ───────────────────────────────────────────────────────
        self.tab_manager = TabManager(self.file_service, self.settings)
        self.tab_manager.tab_changed.connect(self._on_tab_changed)
        self.tab_manager.tab_closed.connect(self._on_tab_closed)
        main_layout.addWidget(self.tab_manager.tab_bar_widget)

        # ── Main Splitter (Sidebar | Editor | AI Panel) ───────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)

        # Sidebar
        self._sidebar = Sidebar(self.file_service)
        self._sidebar.file_opened.connect(self._open_note)
        self._sidebar.new_note_requested.connect(self._create_new_note)
        self._sidebar.file_deleted.connect(self._on_file_deleted)
        self._sidebar.file_renamed.connect(self._on_file_renamed)
        self._sidebar.backlink_clicked.connect(self._open_note)
        self._sidebar.tag_clicked.connect(self._filter_by_tag)
        self._splitter.addWidget(self._sidebar)

        # Editor area
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        self.editor = MarkdownEditor(theme=self.settings.get("theme", "moltin-dark"))
        self.editor.content_changed.connect(self._on_content_changed)
        self.editor.link_clicked.connect(self._on_link_clicked)
        self.editor.ai_action_requested.connect(self._on_ai_action_from_editor)

        editor_layout.addWidget(self.editor)
        self._splitter.addWidget(editor_container)

        # AI Panel
        self._ai_panel = AIPanel(self.ai_manager)
        self._ai_panel.suggestion_accepted.connect(self._on_suggestion_accepted)
        self._splitter.addWidget(self._ai_panel)

        # Set splitter sizes
        sidebar_w = self.settings.get("sidebar_width", 260)
        ai_w = self.settings.get("ai_panel_width", 380)
        total = self.width()
        editor_w = total - sidebar_w - ai_w
        self._splitter.setSizes([sidebar_w, max(editor_w, 400), ai_w])

        main_layout.addWidget(self._splitter, 1)

        # Wire editor selection → AI panel
        self.editor.selectionChanged.connect(self._on_editor_selection_changed)

    def _build_menus(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction(QAction("New Note", self, shortcut="Ctrl+N", triggered=self._create_new_note))
        file_menu.addAction(QAction("Open Vault…", self, shortcut="Ctrl+O", triggered=self._open_vault_dialog))
        file_menu.addAction(QAction("Create New Vault…", self, triggered=self._create_new_vault))
        file_menu.addSeparator()
        file_menu.addAction(QAction("Save", self, shortcut="Ctrl+S", triggered=self._save_current_note))
        file_menu.addSeparator()
        file_menu.addAction(QAction("Settings…", self, shortcut="Ctrl+,", triggered=self._open_settings))
        file_menu.addSeparator()
        file_menu.addAction(QAction("Quit", self, shortcut="Ctrl+Q", triggered=self.close))

        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        edit_menu.addAction(QAction("Undo", self, shortcut="Ctrl+Z", triggered=self.editor.undo))
        edit_menu.addAction(QAction("Redo", self, shortcut="Ctrl+Y", triggered=self.editor.redo))
        edit_menu.addSeparator()
        edit_menu.addAction(QAction("Cut", self, shortcut="Ctrl+X", triggered=self.editor.cut))
        edit_menu.addAction(QAction("Copy", self, shortcut="Ctrl+C", triggered=self.editor.copy))
        edit_menu.addAction(QAction("Paste", self, shortcut="Ctrl+V", triggered=self.editor.paste))
        edit_menu.addSeparator()
        edit_menu.addAction(QAction("Select All", self, shortcut="Ctrl+A", triggered=self.editor.selectAll))

        # View menu
        view_menu = menubar.addMenu("View")
        view_menu.addAction(QAction("Toggle Sidebar", self, shortcut="Ctrl+\\", triggered=self._toggle_sidebar))
        view_menu.addAction(QAction("Toggle AI Panel", self, shortcut="Ctrl+Shift+A", triggered=self._toggle_ai_panel))
        view_menu.addSeparator()
        view_menu.addAction(QAction("Switch Theme", self, shortcut="Ctrl+Shift+T", triggered=self._toggle_theme))
        view_menu.addAction(QAction("Graph View", self, triggered=self._show_graph))

        # Navigate menu
        nav_menu = menubar.addMenu("Navigate")
        nav_menu.addAction(QAction("Quick Open (Ctrl+P)", self, shortcut="Ctrl+P", triggered=self._open_quick_search))
        nav_menu.addAction(QAction("Search Notes", self, shortcut="Ctrl+Shift+F", triggered=self._open_full_search))

        # AI menu
        ai_menu = menubar.addMenu("AI")
        ai_menu.addAction(QAction("Fix Grammar", self, shortcut="Ctrl+Shift+G", triggered=lambda: self._ai_shortcut("grammar")))
        ai_menu.addAction(QAction("Rephrase", self, shortcut="Ctrl+Shift+R", triggered=lambda: self._ai_shortcut("rephrase")))
        ai_menu.addAction(QAction("Expand", self, shortcut="Ctrl+Shift+E", triggered=lambda: self._ai_shortcut("expand")))
        ai_menu.addAction(QAction("Summarise", self, shortcut="Ctrl+Shift+S", triggered=lambda: self._ai_shortcut("summarise")))
        ai_menu.addSeparator()
        ai_menu.addAction(QAction("Open AI Panel", self, triggered=lambda: self._ai_panel.setVisible(True)))

    def _build_shortcuts(self):
        """Additional keyboard shortcuts not covered by menu."""
        from PyQt6.QtGui import QShortcut

        QShortcut(QKeySequence("Ctrl+W"), self, self._close_current_tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self.tab_manager.next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self.tab_manager.prev_tab)

    def _build_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._word_count_label = QLabel("0 words")
        self._vault_status_label = QLabel("No vault")
        self._ai_status_label = QLabel(f"AI: {self.settings.get('ai_provider', 'groq').capitalize()}")

        self._status_bar.addWidget(self._vault_status_label)
        self._status_bar.addPermanentWidget(self._word_count_label)
        self._status_bar.addPermanentWidget(self._ai_status_label)

    # ─── Vault Operations ──────────────────────────────────────────────────────

    def _open_vault_dialog(self):
        path = QFileDialog.getExistingDirectory(
            self, "Open Vault", str(get_vaults_dir())
        )
        if path:
            self._open_vault(path)

    def _create_new_vault(self):
        name, ok = QInputDialog.getText(self, "New Vault", "Vault name:")
        if ok and name.strip():
            vault_path = str(get_vaults_dir() / name.strip())
            os.makedirs(vault_path, exist_ok=True)
            self._open_vault(vault_path)

    def _open_vault(self, path: str):
        self._current_vault_path = path
        vault_name = Path(path).name

        self.file_service.set_vault(path)
        self._sidebar.set_vault(path, vault_name)
        self._refresh_sidebar()

        # Rebuild indexes in background
        threading.Thread(target=self._rebuild_indexes, daemon=True).start()

        self.settings.set("current_vault_path", path)
        self.settings.add_recent_vault(path, vault_name)

        self._vault_status_label.setText(f"📁  {vault_name}")
        self.setWindowTitle(f"{vault_name} — Moltin TypeWriter")
        self._status_bar.showMessage(f"Opened vault: {vault_name}", 3000)

    def _rebuild_indexes(self):
        self.search_service.rebuild_index()
        self.backlink_service.build_index()

        # Update tags panel (must be on main thread)
        QTimer.singleShot(0, self._update_tags_panel)

    def _update_tags_panel(self):
        notes = self.file_service.index_all_notes()
        tag_counts: dict[str, int] = {}
        for note in notes:
            for tag in note.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        self._sidebar.set_tags(tag_counts)

    def _refresh_sidebar(self):
        tree = self.file_service.get_file_tree()
        self._sidebar.refresh_files(tree)

    # ─── Note Operations ───────────────────────────────────────────────────────

    def _open_note(self, path: str):
        if not os.path.isfile(path):
            self._status_bar.showMessage(f"File not found: {path}", 3000)
            return

        note = self.file_service.read_note(path)
        self._current_note_path = path

        # Open in tab manager
        self.tab_manager.open_tab(path, note["name"], note["content"])
        self.editor.set_content(note["content"], path)
        self._update_word_count()

        # Backlinks (background)
        def _load_backlinks():
            backlinks = self.backlink_service.get_backlinks(note["name"])
            QTimer.singleShot(0, lambda: self._sidebar.set_backlinks(note["name"], backlinks))
        threading.Thread(target=_load_backlinks, daemon=True).start()

        self.setWindowTitle(f"{note['name']} — Moltin TypeWriter")
        self._status_bar.showMessage(f"Opened: {note['name']}", 2000)

    def _create_new_note(self):
        if not self._current_vault_path:
            QMessageBox.information(self, "No Vault", "Please open a vault first.")
            return
        name, ok = QInputDialog.getText(self, "New Note", "Note name:")
        if ok and name.strip():
            result = self.file_service.create_note(name.strip())
            self._refresh_sidebar()
            self._open_note(result["path"])

    def _save_current_note(self):
        if self._current_note_path:
            content = self.editor.get_content()
            self.file_service.write_note(self._current_note_path, content)
            self.tab_manager.mark_clean(self._current_note_path)
            self._status_bar.showMessage("Saved", 2000)

    def _on_content_changed(self, content: str):
        """Called by auto-save timer."""
        if self._current_note_path:
            self.file_service.write_note(self._current_note_path, content)
            self.tab_manager.mark_clean(self._current_note_path)
            self._update_word_count()

            # Update backlink index in background
            threading.Thread(
                target=lambda: self.backlink_service.build_index(), daemon=True
            ).start()

    def _on_file_deleted(self, path: str):
        self.tab_manager.close_tab_by_path(path)
        self._refresh_sidebar()
        if self._current_note_path == path:
            self._current_note_path = None
            self.editor.set_content("")

    def _on_file_renamed(self, old_path: str, new_path: str):
        self.tab_manager.rename_tab(old_path, new_path, Path(new_path).stem)
        if self._current_note_path == old_path:
            self._current_note_path = new_path
        self._refresh_sidebar()

    def _on_link_clicked(self, link_name: str):
        """Navigate to a [[wiki link]] target."""
        path = self.file_service.resolve_link(link_name)
        if path:
            self._open_note(path)
        else:
            # Offer to create the note
            reply = QMessageBox.question(
                self, "Note Not Found",
                f"'{link_name}' doesn't exist. Create it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                result = self.file_service.create_note(link_name)
                self._refresh_sidebar()
                self._open_note(result["path"])

    def _on_tab_changed(self, path: str):
        if path and path != self._current_note_path:
            self._open_note(path)

    def _on_tab_closed(self, path: str):
        if path == self._current_note_path:
            # Switch to another open tab or clear editor
            remaining = self.tab_manager.get_open_paths()
            if remaining:
                self._open_note(remaining[-1])
            else:
                self.editor.set_content("")
                self._current_note_path = None
                self.setWindowTitle("Moltin TypeWriter")

    def _close_current_tab(self):
        if self._current_note_path:
            self.tab_manager.close_tab_by_path(self._current_note_path)

    # ─── AI Operations ────────────────────────────────────────────────────────

    def _on_editor_selection_changed(self):
        selected = self.editor.get_selected_text()
        full_doc = self.editor.get_content()
        self._ai_panel.set_selection(selected, full_doc)

    def _on_ai_action_from_editor(self, action: str, selected_text: str):
        """Handle AI action triggered from editor context menu."""
        self._ai_panel.setVisible(True)
        full_doc = self.editor.get_content()
        self._ai_panel.trigger_action(action, selected_text, full_doc)

    def _on_suggestion_accepted(self, original: str, suggested: str):
        """Replace selected text in editor with AI suggestion."""
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(suggested)
        else:
            # No selection — insert at cursor
            cursor.insertText(suggested)
        self.editor.setTextCursor(cursor)

    def _ai_shortcut(self, action: str):
        selected = self.editor.get_selected_text()
        if not selected.strip():
            self._status_bar.showMessage("Select text first to use AI actions", 3000)
            return
        self._ai_panel.setVisible(True)
        self._ai_panel.trigger_action(action, selected, self.editor.get_content())

    # ─── Search ───────────────────────────────────────────────────────────────

    def _open_quick_search(self):
        modal = SearchModal(self.search_service, mode="quick", parent=self)
        modal.note_selected.connect(self._open_note)
        modal.exec()

    def _open_full_search(self):
        modal = SearchModal(self.search_service, mode="full", parent=self)
        modal.note_selected.connect(self._open_note)
        modal.exec()

    def _filter_by_tag(self, tag: str):
        """Open full search pre-filled with tag query."""
        modal = SearchModal(self.search_service, mode="full", parent=self)
        modal._input.setText(f"#{tag}")
        modal._run_search()
        modal.note_selected.connect(self._open_note)
        modal.exec()

    # ─── View Toggles ─────────────────────────────────────────────────────────

    def _toggle_sidebar(self):
        self._sidebar.setVisible(not self._sidebar.isVisible())

    def _toggle_ai_panel(self):
        self._ai_panel.setVisible(not self._ai_panel.isVisible())

    def _toggle_theme(self):
        current = self.settings.get("theme", "moltin-dark")
        new_theme = "moltin-light" if current == "moltin-dark" else "moltin-dark"
        self.settings.set("theme", new_theme)
        from PyQt6.QtWidgets import QApplication
        apply_theme(QApplication.instance(), new_theme)
        self.editor.set_theme(new_theme)
        self._status_bar.showMessage(f"Theme: {new_theme.replace('-', ' ').title()}", 2000)

    def _show_graph(self):
        try:
            from ui.graph_view import GraphView
            graph_data = self.backlink_service.get_link_graph()
            dialog = GraphView(graph_data, self)
            dialog.exec()
        except ImportError:
            QMessageBox.information(self, "Graph View", "Graph view requires PyQtWebEngine.\nRun: pip install PyQtWebEngine")

    # ─── Settings ─────────────────────────────────────────────────────────────

    def _open_settings(self):
        dialog = SettingsDialog(self.settings, parent=self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.theme_changed.connect(self._on_theme_changed_from_settings)
        dialog.exec()

    def _on_settings_changed(self):
        self.ai_manager.settings = self.settings
        provider = self.settings.get("ai_provider", "groq")
        self._ai_panel.update_provider_badge(provider)
        self._ai_status_label.setText(f"AI: {provider.capitalize()}")
        font_size = self.settings.get("font_size", 14)
        font = self.editor.font()
        font.setPointSize(font_size)
        self.editor.setFont(font)

    def _on_theme_changed_from_settings(self, theme: str):
        from PyQt6.QtWidgets import QApplication
        apply_theme(QApplication.instance(), theme)
        self.editor.set_theme(theme)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _update_word_count(self):
        count = self.editor.get_word_count()
        self._word_count_label.setText(f"{count:,} words")

    # ─── Window events ────────────────────────────────────────────────────────

    def closeEvent(self, event):
        # Save window state
        self.settings.update({
            "window_width": self.width(),
            "window_height": self.height(),
            "window_maximized": self.isMaximized(),
        })
        # Save current note
        if self._current_note_path:
            content = self.editor.get_content()
            self.file_service.write_note(self._current_note_path, content)
        event.accept()
