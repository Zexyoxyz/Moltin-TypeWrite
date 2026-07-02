# -- Path bootstrap (works when run directly or via main.py) ------------------
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# -----------------------------------------------------------------------------
"""
Settings Dialog — configure theme, AI providers, editor preferences.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QComboBox, QCheckBox, QSpinBox, QPushButton,
    QLineEdit, QGroupBox, QGridLayout, QScrollArea,
    QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from config.settings import SettingsManager
from config.crypto import encrypt, decrypt


PROVIDERS = ["groq", "openai", "anthropic", "gemini", "ollama"]
PROVIDER_LABELS = {
    "groq": "Groq",
    "openai": "OpenAI (GPT-4o, GPT-4o-mini)",
    "anthropic": "Anthropic Claude",
    "gemini": "Google Gemini",
    "ollama": "Ollama (Local Models)",
}
PROVIDER_URLS = {
    "groq": "https://console.groq.com/keys",
    "openai": "https://platform.openai.com/api-keys",
    "anthropic": "https://console.anthropic.com/settings/keys",
    "gemini": "https://aistudio.google.com/app/apikey",
    "ollama": "https://ollama.ai",
}


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal()
    theme_changed = pyqtSignal(str)

    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings — Moltin TypeWriter")
        self.setMinimumSize(640, 500)
        self.resize(700, 560)
        self._key_inputs: dict[str, QLineEdit] = {}
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.addTab(self._build_appearance_tab(), "Appearance")
        tabs.addTab(self._build_editor_tab(), "Editor")
        tabs.addTab(self._build_ai_tab(), "AI Providers")
        tabs.addTab(self._build_vault_tab(), "Vaults")
        layout.addWidget(tabs, 1)

        # Footer
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 12, 16, 12)

        reset_btn = QPushButton("Reset Defaults")
        reset_btn.clicked.connect(self._reset_defaults)

        save_btn = QPushButton("Save & Close")
        save_btn.setObjectName("btn_primary")
        save_btn.clicked.connect(self._save)

        footer_layout.addWidget(reset_btn)
        footer_layout.addStretch()
        footer_layout.addWidget(save_btn)
        layout.addWidget(footer)

    def _build_appearance_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # Theme
        theme_label = QLabel("THEME")
        theme_label.setObjectName("section_label")
        layout.addWidget(theme_label)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Moltin Dark", "Moltin Light"])
        layout.addWidget(self._theme_combo)

        # Font Size
        size_label = QLabel("EDITOR FONT SIZE")
        size_label.setObjectName("section_label")
        layout.addWidget(size_label)

        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(10, 24)
        self._font_size_spin.setSuffix(" px")
        layout.addWidget(self._font_size_spin)

        layout.addStretch()
        return w

    def _build_editor_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        behavior_label = QLabel("EDITOR BEHAVIOUR")
        behavior_label.setObjectName("section_label")
        layout.addWidget(behavior_label)

        self._auto_save_check = QCheckBox("Auto-save (1 second delay)")
        self._line_numbers_check = QCheckBox("Show line numbers")
        self._word_wrap_check = QCheckBox("Word wrap")
        self._spell_check = QCheckBox("Spell check")

        for cb in [self._auto_save_check, self._line_numbers_check,
                   self._word_wrap_check, self._spell_check]:
            layout.addWidget(cb)

        layout.addStretch()
        return w

    def _build_ai_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 16, 24, 16)
        content_layout.setSpacing(12)

        # Active provider
        active_label = QLabel("ACTIVE PROVIDER")
        active_label.setObjectName("section_label")
        content_layout.addWidget(active_label)

        self._provider_combo = QComboBox()
        for p in PROVIDERS:
            self._provider_combo.addItem(PROVIDER_LABELS[p], p)
        content_layout.addWidget(self._provider_combo)

        # API Keys
        keys_label = QLabel("API KEYS")
        keys_label.setObjectName("section_label")
        content_layout.addWidget(keys_label)

        for provider in PROVIDERS:
            group = QGroupBox(PROVIDER_LABELS[provider])
            group_layout = QVBoxLayout(group)

            key_row = QHBoxLayout()
            key_input = QLineEdit()
            key_input.setEchoMode(QLineEdit.EchoMode.Password)
            key_input.setPlaceholderText(
                f"Enter your {provider.upper()} API key"
            )
            show_btn = QPushButton("👁")
            show_btn.setFixedWidth(32)
            show_btn.setCheckable(True)
            show_btn.toggled.connect(lambda checked, ki=key_input: ki.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            ))
            key_row.addWidget(key_input)
            key_row.addWidget(show_btn)
            group_layout.addLayout(key_row)

            if provider in PROVIDER_URLS:
                link = QLabel(f'<a href="{PROVIDER_URLS[provider]}" style="color:#9d7ef5;">Get API key →</a>')
                link.setOpenExternalLinks(True)
                group_layout.addWidget(link)

            if provider == "ollama":
                ollama_note = QLabel("Ollama runs locally. Install from ollama.ai, no key needed.")
                ollama_note.setObjectName("ai_explanation_text")
                ollama_note.setWordWrap(True)
                group_layout.addWidget(ollama_note)

            self._key_inputs[provider] = key_input
            content_layout.addWidget(group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return w

    def _build_vault_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        vaults_label = QLabel("RECENT VAULTS")
        vaults_label.setObjectName("section_label")
        layout.addWidget(vaults_label)

        recent = self.settings.get_recent_vaults()
        if recent:
            for v in recent:
                row = QHBoxLayout()
                name_label = QLabel(f"📁  {v['name']}")
                path_label = QLabel(v["path"])
                path_label.setObjectName("ai_explanation_text")
                row.addWidget(name_label)
                row.addStretch()
                row.addWidget(path_label)
                layout.addLayout(row)
        else:
            layout.addWidget(QLabel("No recent vaults"))

        layout.addStretch()
        return w

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load_values(self):
        theme = self.settings.get("theme", "moltin-dark")
        self._theme_combo.setCurrentIndex(0 if theme == "moltin-dark" else 1)
        self._font_size_spin.setValue(self.settings.get("font_size", 14))
        self._auto_save_check.setChecked(True)
        self._line_numbers_check.setChecked(self.settings.get("show_line_numbers", True))
        self._word_wrap_check.setChecked(self.settings.get("word_wrap", True))
        self._spell_check.setChecked(self.settings.get("spell_check", True))

        # Active provider
        active = self.settings.get("ai_provider", "groq")
        for i, p in enumerate(PROVIDERS):
            if p == active:
                self._provider_combo.setCurrentIndex(i)
                break

        # API keys — show placeholder, don't reveal stored keys
        encrypted_keys = self.settings.get("encrypted_keys", {})
        for provider, key_input in self._key_inputs.items():
            if provider in encrypted_keys:
                key_input.setPlaceholderText("••••••••••••••••••••  (key stored)")

    def _save(self):
        theme = "moltin-dark" if self._theme_combo.currentIndex() == 0 else "moltin-light"
        old_theme = self.settings.get("theme")

        self.settings.update({
            "theme": theme,
            "font_size": self._font_size_spin.value(),
            "show_line_numbers": self._line_numbers_check.isChecked(),
            "word_wrap": self._word_wrap_check.isChecked(),
            "spell_check": self._spell_check.isChecked(),
            "ai_provider": self._provider_combo.currentData(),
        })

        # Save API keys (encrypt non-empty entries)
        encrypted_keys = dict(self.settings.get("encrypted_keys", {}))
        for provider, key_input in self._key_inputs.items():
            raw = key_input.text().strip()
            if raw:
                encrypted_keys[provider] = encrypt(raw)
        self.settings.set("encrypted_keys", encrypted_keys)

        if theme != old_theme:
            self.theme_changed.emit(theme)

        self.settings_changed.emit()
        self.accept()

    def _reset_defaults(self):
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Reset all settings to defaults? Your notes and API keys will not be affected.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.reset()
            self.settings_changed.emit()
            self.accept()
