# -- Path bootstrap (works when run directly or via main.py) ------------------
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# -----------------------------------------------------------------------------
"""
AI Panel — slide-out assistant panel on the right side of the editor.
Provides all AI writing actions with suggestion display and explain cards.
"""

import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QTextEdit, QGridLayout, QComboBox, QSizePolicy,
    QFrame, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QObject
from PyQt6.QtGui import QFont
from services.ai.ai_manager import AIManager


# ─── Background AI Worker ─────────────────────────────────────────────────────

class AIWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, ai_manager: AIManager, action: str, selected_text: str,
                 full_document: str = "", tone: str | None = None):
        super().__init__()
        self.ai_manager = ai_manager
        self.action = action
        self.selected_text = selected_text
        self.full_document = full_document
        self.tone = tone

    @pyqtSlot()
    def run(self):
        try:
            result = self.ai_manager.request(
                action=self.action,
                selected_text=self.selected_text,
                full_document=self.full_document or None,
                tone=self.tone,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ─── AI Panel ─────────────────────────────────────────────────────────────────

class AIPanel(QWidget):
    suggestion_accepted = pyqtSignal(str, str)  # original, suggested
    suggestion_dismissed = pyqtSignal()

    ACTIONS = [
        ("grammar",     "Fix Grammar",      "✓"),
        ("spelling",    "Spelling",         "Aa"),
        ("clarity",     "Clarity",          "◎"),
        ("restructure", "Restructure",      "⇄"),
        ("rephrase",    "Rephrase",         "↺"),
        ("expand",      "Expand",           "↗"),
        ("summarise",   "Summarise",        "⊟"),
        ("brainstorm",  "Brainstorm",       "✦"),
        ("explain",     "Analyse",          "?"),
        ("style-check", "Style Check",      "≡"),
    ]

    TONES = ["Professional", "Casual", "Academic", "Friendly", "Persuasive"]

    def __init__(self, ai_manager: AIManager, parent=None):
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.setObjectName("ai_panel")
        self.setMinimumWidth(320)
        self.setMaximumWidth(450)
        self._current_selection = ""
        self._current_full_doc = ""
        self._worker: AIWorker | None = None
        self._thread: QThread | None = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("ai_panel_header")
        header.setFixedHeight(60)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel("✦ AI Assistant")
        title.setObjectName("ai_title")

        self._provider_badge = QLabel(f"Groq")
        self._provider_badge.setObjectName("ai_provider_badge")

        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addWidget(self._provider_badge)
        layout.addWidget(header)

        # ── Scroll area for content ──────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        self._content_layout = QVBoxLayout(content_widget)
        self._content_layout.setContentsMargins(8, 8, 8, 8)
        self._content_layout.setSpacing(8)

        # ── Action buttons grid ──────────────────────────────────────────────
        actions_label = QLabel("ACTIONS")
        actions_label.setObjectName("section_label")
        self._content_layout.addWidget(actions_label)

        grid_widget = QWidget()
        grid_widget.setObjectName("ai_action_grid")
        grid = QGridLayout(grid_widget)
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)

        for i, (action_id, label, icon) in enumerate(self.ACTIONS):
            btn = QPushButton(f"{icon}  {label}")
            btn.setToolTip(f"AI: {label}")
            btn.clicked.connect(lambda checked, a=action_id: self._trigger_action(a))
            grid.addWidget(btn, i // 2, i % 2)

        self._content_layout.addWidget(grid_widget)

        # ── Tone selector ────────────────────────────────────────────────────
        tone_label = QLabel("TONE ADJUSTMENT")
        tone_label.setObjectName("section_label")
        self._content_layout.addWidget(tone_label)

        tone_row = QHBoxLayout()
        self._tone_combo = QComboBox()
        self._tone_combo.addItems(self.TONES)
        tone_btn = QPushButton("Apply Tone")
        tone_btn.setObjectName("btn_primary")
        tone_btn.clicked.connect(self._trigger_tone)
        tone_row.addWidget(self._tone_combo, 1)
        tone_row.addWidget(tone_btn)
        self._content_layout.addLayout(tone_row)

        # ── Loading indicator ────────────────────────────────────────────────
        self._loading_label = QLabel("✦ Thinking...")
        self._loading_label.setObjectName("ai_loading")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.hide()
        self._content_layout.addWidget(self._loading_label)

        # ── Suggestion card ──────────────────────────────────────────────────
        self._suggestion_card = QWidget()
        self._suggestion_card.setObjectName("ai_suggestion_card")
        self._suggestion_card.hide()
        card_layout = QVBoxLayout(self._suggestion_card)
        card_layout.setSpacing(8)

        card_title = QLabel("SUGGESTION")
        card_title.setObjectName("section_label")
        card_layout.addWidget(card_title)

        self._suggestion_text = QTextEdit()
        self._suggestion_text.setObjectName("ai_suggestion_text")
        self._suggestion_text.setReadOnly(False)
        self._suggestion_text.setMinimumHeight(120)
        self._suggestion_text.setMaximumHeight(300)
        card_layout.addWidget(self._suggestion_text)

        explain_title = QLabel("WHY THIS CHANGE")
        explain_title.setObjectName("section_label")
        card_layout.addWidget(explain_title)

        self._explanation_text = QLabel()
        self._explanation_text.setObjectName("ai_explanation_text")
        self._explanation_text.setWordWrap(True)
        card_layout.addWidget(self._explanation_text)

        # Accept / Dismiss buttons
        btn_row = QHBoxLayout()
        self._accept_btn = QPushButton("✓  Accept")
        self._accept_btn.setObjectName("btn_accept")
        self._accept_btn.clicked.connect(self._accept_suggestion)

        self._dismiss_btn = QPushButton("✕  Dismiss")
        self._dismiss_btn.setObjectName("btn_dismiss")
        self._dismiss_btn.clicked.connect(self._dismiss_suggestion)

        btn_row.addWidget(self._accept_btn)
        btn_row.addWidget(self._dismiss_btn)
        card_layout.addLayout(btn_row)

        self._content_layout.addWidget(self._suggestion_card)
        self._content_layout.addStretch()

        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)

        # ── Footer ───────────────────────────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(32)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 0, 12, 0)
        self._status_label = QLabel("Ready")
        self._status_label.setObjectName("section_label")
        footer_layout.addWidget(self._status_label)
        layout.addWidget(footer)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_selection(self, text: str, full_doc: str = "") -> None:
        """Called by the editor when selection changes."""
        self._current_selection = text
        self._current_full_doc = full_doc

    def trigger_action(self, action: str, selected_text: str, full_doc: str = "") -> None:
        """Trigger an AI action from outside (e.g. keyboard shortcut)."""
        self._current_selection = selected_text
        self._current_full_doc = full_doc
        self._run_ai(action)

    def update_provider_badge(self, provider: str) -> None:
        self._provider_badge.setText(provider.capitalize())

    # ── Private ───────────────────────────────────────────────────────────────

    def _trigger_action(self, action: str) -> None:
        if not self._current_selection.strip():
            self._set_status("⚠ Select text in the editor first")
            return
        self._run_ai(action)

    def _trigger_tone(self) -> None:
        if not self._current_selection.strip():
            self._set_status("⚠ Select text in the editor first")
            return
        tone = self._tone_combo.currentText().lower()
        self._run_ai(f"tone:{tone}", tone=tone)

    def _run_ai(self, action: str, tone: str | None = None) -> None:
        # Parse tone from action string like "tone:professional"
        actual_action = action
        if action.startswith("tone:"):
            tone = action.split(":", 1)[1]
            actual_action = "tone"

        self._loading_label.show()
        self._suggestion_card.hide()
        self._set_status("✦ Requesting AI...")

        # Run in background thread
        self._thread = QThread()
        self._worker = AIWorker(
            self.ai_manager, actual_action,
            self._current_selection, self._current_full_doc, tone
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_ai_finished)
        self._worker.error.connect(self._on_ai_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    @pyqtSlot(dict)
    def _on_ai_finished(self, result: dict) -> None:
        self._loading_label.hide()
        self._suggestion_text.setPlainText(result.get("suggestedText", ""))
        self._explanation_text.setText(result.get("explanation", ""))
        self._suggestion_card.show()
        self._set_status(f"✓ Suggestion ready ({result.get('provider', 'ai')})")

    @pyqtSlot(str)
    def _on_ai_error(self, error: str) -> None:
        self._loading_label.hide()
        self._set_status(f"⚠ Error: {error[:80]}")
        if "No API key configured" in error:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "API Key Required", error)

    def _accept_suggestion(self) -> None:
        suggested = self._suggestion_text.toPlainText()
        self.suggestion_accepted.emit(self._current_selection, suggested)
        self._suggestion_card.hide()
        self._set_status("✓ Applied")

    def _dismiss_suggestion(self) -> None:
        self._suggestion_card.hide()
        self.suggestion_dismissed.emit()
        self._set_status("Dismissed")

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)
