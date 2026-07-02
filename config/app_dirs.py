"""
Application directory bootstrap.
Creates all required AppData folders on first run.
"""

import os
import json
from pathlib import Path


def get_app_data_dir() -> Path:
    """Returns the base AppData directory for Moltin TypeWriter."""
    base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return base / "MoltinTypeWriter"


def get_vaults_dir() -> Path:
    return get_app_data_dir() / "vaults"


def get_backups_dir() -> Path:
    return get_app_data_dir() / "backups"


def get_plugins_dir() -> Path:
    return get_app_data_dir() / "plugins"


def get_settings_path() -> Path:
    return get_app_data_dir() / "settings.json"


def ensure_app_dirs() -> None:
    """Create all required application directories if they don't exist."""
    dirs = [
        get_app_data_dir(),
        get_vaults_dir(),
        get_backups_dir(),
        get_plugins_dir(),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Create example vault if no vaults exist
    vaults_dir = get_vaults_dir()
    example_dir = vaults_dir / "My Notes"
    if not any(vaults_dir.iterdir()):
        example_dir.mkdir(exist_ok=True)
        _create_example_vault(example_dir)


def _create_example_vault(vault_path: Path) -> None:
    """Populate a fresh vault with example notes."""
    welcome = vault_path / "Welcome.md"
    welcome.write_text(
        """# Welcome to Moltin TypeWriter 🖊️

Welcome to your new knowledge base! This is your first note.

## Getting Started

- **Create notes** with `Ctrl+N`
- **Search** your vault with `Ctrl+P` (quick switch) or `Ctrl+Shift+F` (full search)
- **Link notes** using `[[Note Name]]` wiki links
- **Add tags** with `#tag` anywhere in a note
- **Open AI assistant** with `Ctrl+Shift+A`

## AI Writing Assistant

Moltin TypeWriter includes a powerful AI assistant. Select any text and press `Ctrl+Shift+A` to:

- Fix grammar and spelling
- Rephrase or expand your ideas
- Adjust the tone (professional, casual, academic)
- Summarise long passages
- Brainstorm ideas

## Wiki Links

You can link to other notes like this: [[AI Writing Guide]]

Click on any `[[link]]` while holding Ctrl to navigate to that note.

## Tags

Add tags to your notes: #getting-started #tutorial #moltin

---

*Start writing — your ideas deserve a great home.*
""",
        encoding="utf-8",
    )

    ai_guide = vault_path / "AI Writing Guide.md"
    ai_guide.write_text(
        """# AI Writing Guide

tags: #ai #writing #guide

This note explains all AI features available in [[Welcome]].

## Available Actions

| Action | Description |
|--------|-------------|
| Grammar | Fix grammar errors |
| Spelling | Correct spelling mistakes |
| Restructure | Improve logical flow |
| Clarity | Simplify complex sentences |
| Tone | Adjust writing style |
| Rephrase | Use different words, same meaning |
| Expand | Turn brief notes into paragraphs |
| Summarise | Condense long passages |
| Brainstorm | Generate related ideas |
| Autocomplete | Continue your writing |
| Style Check | Consistency across the whole doc |

## How to Use

1. **Select text** in the editor
2. **Right-click** for context menu, or press `Ctrl+Shift+A` to open the AI panel
3. Choose an action
4. Review the suggestion and explanation
5. Click **Accept** to apply, or **Dismiss** to keep your original

## Providers

Moltin TypeWriter works with multiple AI providers:
- **Groq** (recommended)
- OpenAI, Anthropic Claude, Google Gemini, Ollama (local)

Go to **Settings → AI** to add your own API keys.
""",
        encoding="utf-8",
    )
