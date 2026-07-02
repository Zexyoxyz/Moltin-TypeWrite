"""
Settings manager — persists and retrieves all application settings.
Settings are stored in %AppData%/MoltinTypeWriter/settings.json.
"""

import json
from pathlib import Path
from typing import Any

from config.app_dirs import get_settings_path


DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "moltin-dark",
    "font_size": 14,
    "font_family": "JetBrains Mono, Consolas, monospace",
    "line_height": 1.6,
    "auto_save_delay": 1000,
    "spell_check": True,
    "ai_provider": "groq",
    "encrypted_keys": {},          # populated on first run
    "recent_vaults": [],
    "current_vault_path": None,
    "show_line_numbers": True,
    "word_wrap": True,
    "default_view": "edit",
    "sidebar_width": 260,
    "ai_panel_width": 380,
    "window_width": 1400,
    "window_height": 900,
    "window_maximized": False,
}


class SettingsManager:
    def __init__(self):
        self._path = get_settings_path()
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data = {**DEFAULT_SETTINGS, **saved}
            except Exception:
                self._data = dict(DEFAULT_SETTINGS)
        else:
            self._data = dict(DEFAULT_SETTINGS)


    def _save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Settings] Failed to save: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def get_all(self) -> dict[str, Any]:
        return dict(self._data)

    def update(self, updates: dict[str, Any]) -> None:
        self._data.update(updates)
        self._save()

    def reset(self) -> None:
        self._data = dict(DEFAULT_SETTINGS)
        self._save()

    # ── Vault helpers ────────────────────────────────────────────────────────

    def add_recent_vault(self, path: str, name: str) -> None:
        recent = self._data.get("recent_vaults", [])
        # Remove if already present
        recent = [v for v in recent if v["path"] != path]
        recent.insert(0, {"path": path, "name": name})
        self._data["recent_vaults"] = recent[:10]
        self._save()

    def get_recent_vaults(self) -> list[dict[str, str]]:
        return self._data.get("recent_vaults", [])
