# -- Path bootstrap (works when run directly or via main.py) ------------------
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# -----------------------------------------------------------------------------
"""
MarkdownEditor — the core editing widget.

Features:
- Syntax highlighting for Markdown (headings, bold, italic, code, links, wiki links, tags)
- Line numbers
- Auto-save with debounce
- Undo/Redo
- Context menu with AI actions
- Wiki link navigation (Ctrl+Click)
"""

import re
from PyQt6.QtWidgets import (
    QWidget, QPlainTextEdit, QHBoxLayout, QLabel,
    QTextEdit, QMenu, QApplication
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QRect, QSize, QPoint
)
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont,
    QPainter, QTextCursor, QKeySequence, QAction, QPalette
)


# ─── Markdown Syntax Highlighter ─────────────────────────────────────────────

class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, document, theme: str = "moltin-dark"):
        super().__init__(document)
        self.theme = theme
        self._build_rules()

    def _build_rules(self):
        dark = self.theme != "moltin-light"

        def fmt(color: str, bold=False, italic=False, size_delta=0) -> QTextCharFormat:
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            if italic:
                f.setFontItalic(True)
            if size_delta:
                f.setFontPointSize(14 + size_delta)
            return f

        if dark:
            self.rules = [
                # H1–H6
                (re.compile(r"^#{1}\s+.+$", re.MULTILINE), fmt("#f4f4f5", bold=True, size_delta=12)),
                (re.compile(r"^#{2}\s+.+$", re.MULTILINE), fmt("#e4e4e7", bold=True, size_delta=8)),
                (re.compile(r"^#{3}\s+.+$", re.MULTILINE), fmt("#d4d4d8", bold=True, size_delta=4)),
                (re.compile(r"^#{4,6}\s+.+$", re.MULTILINE), fmt("#a1a1aa", bold=True, size_delta=2)),
                # Bold
                (re.compile(r"\*\*(.+?)\*\*|__(.+?)__"), fmt("#ffffff", bold=True)),
                # Italic
                (re.compile(r"\*(.+?)\*|_(.+?)_"), fmt("#a1a1aa", italic=True)),
                # Inline code
                (re.compile(r"`[^`]+`"), fmt("#34d399")),
                # Code block
                (re.compile(r"```[\s\S]*?```", re.DOTALL), fmt("#34d399")),
                # Wiki links [[...]]
                (re.compile(r"\[\[([^\]]+)\]\]"), fmt("#a78bfa", bold=True)),
                # Regular links [text](url)
                (re.compile(r"\[([^\]]+)\]\([^\)]+\)"), fmt("#60a5fa")),
                # Tags #tag
                (re.compile(r"(?:^|\s)(#[a-zA-Z0-9_/-]+)"), fmt("#34d399", bold=True)),
                # Blockquote
                (re.compile(r"^>\s+.+$", re.MULTILINE), fmt("#71717a", italic=True)),
                # Horizontal rule
                (re.compile(r"^[-*_]{3,}\s*$", re.MULTILINE), fmt("#3f3f46")),
                # List bullets
                (re.compile(r"^[\s]*[-*+]\s", re.MULTILINE), fmt("#8b5cf6")),
                # Numbered list
                (re.compile(r"^\s*\d+\.\s", re.MULTILINE), fmt("#8b5cf6")),
                # Frontmatter
                (re.compile(r"^---\s*$", re.MULTILINE), fmt("#52525b")),
            ]
        else:
            self.rules = [
                (re.compile(r"^#{1}\s+.+$", re.MULTILINE), fmt("#18181b", bold=True, size_delta=12)),
                (re.compile(r"^#{2}\s+.+$", re.MULTILINE), fmt("#27272a", bold=True, size_delta=8)),
                (re.compile(r"^#{3}\s+.+$", re.MULTILINE), fmt("#3f3f46", bold=True, size_delta=4)),
                (re.compile(r"^#{4,6}\s+.+$", re.MULTILINE), fmt("#52525b", bold=True, size_delta=2)),
                (re.compile(r"\*\*(.+?)\*\*|__(.+?)__"), fmt("#000000", bold=True)),
                (re.compile(r"\*(.+?)\*|_(.+?)_"), fmt("#52525b", italic=True)),
                (re.compile(r"`[^`]+`"), fmt("#059669")),
                (re.compile(r"```[\s\S]*?```", re.DOTALL), fmt("#059669")),
                (re.compile(r"\[\[([^\]]+)\]\]"), fmt("#4f46e5", bold=True)),
                (re.compile(r"\[([^\]]+)\]\([^\)]+\)"), fmt("#2563eb")),
                (re.compile(r"(?:^|\s)(#[a-zA-Z0-9_/-]+)"), fmt("#059669", bold=True)),
                (re.compile(r"^>\s+.+$", re.MULTILINE), fmt("#a1a1aa", italic=True)),
                (re.compile(r"^[-*_]{3,}\s*$", re.MULTILINE), fmt("#d4d4d8")),
                (re.compile(r"^[\s]*[-*+]\s", re.MULTILINE), fmt("#6366f1")),
                (re.compile(r"^\s*\d+\.\s", re.MULTILINE), fmt("#6366f1")),
                (re.compile(r"^---\s*$", re.MULTILINE), fmt("#a1a1aa")),
            ]
    def highlightBlock(self, text: str):
        full_text = self.document().toPlainText()
        block_start = self.currentBlock().position()

        for pattern, fmt in self.rules:
            for match in pattern.finditer(full_text):
                start = match.start() - block_start
                end = match.end() - block_start
                length = match.end() - match.start()

                # Only highlight if match is within this block
                if start < 0 and end <= 0:
                    continue
                if start >= len(text):
                    continue

                # Clamp to block
                local_start = max(0, start)
                local_end = min(len(text), end)
                if local_start < local_end:
                    self.setFormat(local_start, local_end - local_start, fmt)


# ─── Line Number Area ─────────────────────────────────────────────────────────

class LineNumberArea(QWidget):
    def __init__(self, editor: "MarkdownEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_line_numbers(event)


# ─── Main Editor Widget ───────────────────────────────────────────────────────

class MarkdownEditor(QPlainTextEdit):
    # Emitted when content changes (for auto-save)
    content_changed = pyqtSignal(str)
    # Emitted when a wiki link is ctrl+clicked
    link_clicked = pyqtSignal(str)
    # Emitted when AI action requested from context menu
    ai_action_requested = pyqtSignal(str, str)  # action, selected_text

    WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")

    def __init__(self, parent=None, theme: str = "moltin-dark"):
        super().__init__(parent)
        self.theme = theme
        self._current_path: str | None = None

        self._setup_editor()
        self._setup_line_numbers()
        self._setup_auto_save()
        self._setup_highlighter()

    def _setup_editor(self):
        self.setObjectName("editor_container")
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setTabStopDistance(28)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        
        # Protect title line from context menu Cut/Delete/Paste
        first_block = self.document().findBlockByNumber(0)
        if first_block.text().startswith("# "):
            cursor = self.textCursor()
            end_pos = first_block.position() + first_block.length() - 1
            if cursor.hasSelection() and cursor.selectionStart() <= end_pos:
                for action in menu.actions():
                    if action.text() in ("Cu&t", "Cut", "Delete", "&Delete", "&Paste", "Paste"):
                        action.setEnabled(False)
            elif cursor.position() <= end_pos:
                for action in menu.actions():
                    if action.text() in ("Cu&t", "Cut", "Delete", "&Delete", "&Paste", "Paste"):
                        action.setEnabled(False)

        menu.addSeparator()
        ai_action = menu.addAction("✨ AI Edit")
        action = menu.exec(event.globalPos())
        if action == ai_action:
            self._show_context_menu(event.pos()) # Reuse custom logic
            
    def dropEvent(self, event):
        # Prevent dropping text into the title line
        first_block = self.document().findBlockByNumber(0)
        if first_block.text().startswith("# "):
            cursor = self.cursorForPosition(event.position().toPoint())
            end_pos = first_block.position() + first_block.length() - 1
            if cursor.position() <= end_pos:
                event.ignore()
                return
        super().dropEvent(event)

    def _setup_line_numbers(self):
        self._line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_line_number_width(0)

    def _setup_auto_save(self):
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(1000)
        self._save_timer.timeout.connect(self._emit_save)
        self.textChanged.connect(self._on_text_changed)

    def _setup_highlighter(self):
        self._highlighter = MarkdownHighlighter(self.document(), self.theme)

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        first_block = self.document().findBlockByNumber(0)
        
        # Protect the first line if it's a title (starts with "# ")
        if first_block.text().startswith("# "):
            start_pos = first_block.position()
            end_pos = start_pos + first_block.length() - 1  # end of line text (before \n)
            
            sel_start = cursor.selectionStart()
            pos = cursor.position()
            
            def is_modifying():
                if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                    return True
                if event.matches(QKeySequence.StandardKey.Cut) or event.matches(QKeySequence.StandardKey.Paste):
                    return True
                if event.text() and not event.matches(QKeySequence.StandardKey.Copy) and not event.matches(QKeySequence.StandardKey.SelectAll):
                    if event.text().isprintable():
                        return True
                return False

            if is_modifying():
                if cursor.hasSelection() and sel_start <= end_pos:
                    return # Block if selection overlaps title
                elif not cursor.hasSelection():
                    if pos <= end_pos:
                        return # Block typing inside title
                    if pos == end_pos + 1 and event.key() == Qt.Key.Key_Backspace:
                        return # Block backspacing the newline after title

        super().keyPressEvent(event)

    def set_theme(self, theme: str):
        self.theme = theme
        self._highlighter.theme = theme
        self._highlighter._build_rules()
        self._highlighter.rehighlight()

    # ── Content ───────────────────────────────────────────────────────────────

    def set_content(self, content: str, path: str | None = None):
        self._current_path = path
        # Block signals to avoid triggering auto-save on load
        self.blockSignals(True)
        self.setPlainText(content)
        self.blockSignals(False)
        self._highlighter.rehighlight()

    def get_content(self) -> str:
        return self.toPlainText()

    def get_selected_text(self) -> str:
        cursor = self.textCursor()
        return cursor.selectedText().replace("\u2029", "\n")

    def get_word_count(self) -> int:
        text = self.toPlainText()
        return len(text.split()) if text.strip() else 0

    # ── Auto-save ─────────────────────────────────────────────────────────────

    def _on_text_changed(self):
        self._save_timer.start()

    def _emit_save(self):
        self.content_changed.emit(self.toPlainText())

    # ── Line Numbers ──────────────────────────────────────────────────────────

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def paint_line_numbers(self, event):
        dark = self.theme != "moltin-light"
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#0d0f14" if dark else "#f0f1f8"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#3a3e52" if dark else "#c0c2d0"))
                painter.setFont(self.font())
                painter.drawText(
                    0, top,
                    self._line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    # ── Context Menu (right-click) ─────────────────────────────────────────────

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setObjectName("editor_context_menu")

        has_selection = bool(self.get_selected_text().strip())

        # Standard edit actions
        menu.addAction(QAction("Undo", self, shortcut="Ctrl+Z", triggered=self.undo))
        menu.addAction(QAction("Redo", self, shortcut="Ctrl+Y", triggered=self.redo))
        menu.addSeparator()
        menu.addAction(QAction("Cut", self, shortcut="Ctrl+X", triggered=self.cut))
        menu.addAction(QAction("Copy", self, shortcut="Ctrl+C", triggered=self.copy))
        menu.addAction(QAction("Paste", self, shortcut="Ctrl+V", triggered=self.paste))
        menu.addSeparator()

        if has_selection:
            ai_menu = menu.addMenu("✦ AI Assistant")
            actions = [
                ("grammar",     "Fix Grammar"),
                ("spelling",    "Fix Spelling"),
                ("clarity",     "Improve Clarity"),
                ("restructure", "Restructure"),
                ("rephrase",    "Rephrase"),
                ("expand",      "Expand Idea"),
                ("summarise",   "Summarise"),
                ("brainstorm",  "Brainstorm"),
                ("explain",     "Explain / Analyse"),
            ]
            tone_menu = ai_menu.addMenu("Adjust Tone →")
            for tone in ["Professional", "Casual", "Academic", "Friendly", "Persuasive"]:
                tone_action = QAction(tone, self)
                t = tone.lower()
                sel = self.get_selected_text()
                tone_action.triggered.connect(
                    lambda checked, _t=t, _s=sel: self.ai_action_requested.emit(f"tone:{_t}", _s)
                )
                tone_menu.addAction(tone_action)
            ai_menu.addSeparator()
            for action_id, label in actions:
                act = QAction(label, self)
                sel = self.get_selected_text()
                act.triggered.connect(
                    lambda checked, a=action_id, s=sel: self.ai_action_requested.emit(a, s)
                )
                ai_menu.addAction(act)

        # Wiki link navigation
        cursor = self.cursorForPosition(pos)
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word_pos = cursor.position()
        link = self._get_wiki_link_at(word_pos)
        if link:
            menu.addSeparator()
            act = QAction(f"Open → {link}", self)
            act.triggered.connect(lambda: self.link_clicked.emit(link))
            menu.addAction(act)

        menu.exec(self.mapToGlobal(pos))

    # ── Wiki Link Detection ───────────────────────────────────────────────────

    def _get_wiki_link_at(self, cursor_pos: int) -> str | None:
        """Returns the target of a [[wiki link]] at the cursor position, or None."""
        text = self.toPlainText()
        for match in self.WIKI_LINK_RE.finditer(text):
            if match.start() <= cursor_pos <= match.end():
                return match.group(1).strip()
        return None

    def mousePressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            cursor = self.cursorForPosition(event.pos())
            link = self._get_wiki_link_at(cursor.position())
            if link:
                self.link_clicked.emit(link)
                return
        super().mousePressEvent(event)

    # ── Keyboard Shortcuts ────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        # Bold: Ctrl+B
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_B:
            self._wrap_selection("**", "**")
            return
        # Italic: Ctrl+I
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_I:
            self._wrap_selection("*", "*")
            return
        # Code: Ctrl+`
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_QuoteLeft:
            self._wrap_selection("`", "`")
            return
        # Auto-close brackets/quotes
        pairs = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
        if event.text() in pairs and self.get_selected_text():
            close = pairs[event.text()]
            cursor = self.textCursor()
            selected = cursor.selectedText()
            cursor.insertText(f"{event.text()}{selected}{close}")
            return
        super().keyPressEvent(event)

    def _wrap_selection(self, before: str, after: str):
        cursor = self.textCursor()
        selected = cursor.selectedText()
        if selected:
            cursor.insertText(f"{before}{selected}{after}")
        else:
            pos = cursor.position()
            cursor.insertText(f"{before}{after}")
            cursor.setPosition(pos + len(before))
            self.setTextCursor(cursor)
