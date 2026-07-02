# -- Path bootstrap ------------------------------------------------------------
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# -----------------------------------------------------------------------------
"""
FileService — filesystem operations for notes and vaults.
Reads, writes, creates, renames, and indexes .md files.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Optional

NOTE_EXTENSIONS = {".md", ".markdown", ".txt"}
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
TAG_RE = re.compile(r"(?:^|\s)#([a-zA-Z0-9_/-]+)")


class FileService:
    def __init__(self):
        self.vault_path: Optional[Path] = None

    def set_vault(self, path: str) -> None:
        self.vault_path = Path(path)

    # ── File Tree ─────────────────────────────────────────────────────────────

    def get_file_tree(self) -> list[dict]:
        if not self.vault_path:
            return []
        return self._build_tree(self.vault_path, 0)

    def _build_tree(self, directory: Path, depth: int) -> list[dict]:
        nodes = []
        try:
            entries = sorted(directory.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
        except PermissionError:
            return []

        for entry in entries:
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                nodes.append({
                    "name": entry.name,
                    "path": str(entry),
                    "type": "folder",
                    "children": self._build_tree(entry, depth + 1),
                    "depth": depth,
                })
            elif entry.suffix.lower() in NOTE_EXTENSIONS:
                nodes.append({
                    "name": entry.name,
                    "path": str(entry),
                    "type": "file",
                    "depth": depth,
                })
        return nodes

    # ── Note CRUD ─────────────────────────────────────────────────────────────

    def read_note(self, file_path: str) -> dict:
        p = Path(file_path)
        content = p.read_text(encoding="utf-8")
        stat = p.stat()
        name = p.stem
        relative = str(p.relative_to(self.vault_path)) if self.vault_path else file_path
        return {
            "path": file_path,
            "name": name,
            "relativePath": relative,
            "content": content,
            "tags": self._extract_tags(content),
            "links": self._extract_links(content),
            "modified": stat.st_mtime,
            "size": stat.st_size,
        }

    def write_note(self, file_path: str, content: str) -> None:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def create_note(self, name: str, folder_path: Optional[str] = None) -> dict:
        directory = Path(folder_path) if folder_path else self.vault_path or Path(".")
        safe_name = re.sub(r'[<>:"/\\|?*]', "-", name).strip()
        file_name = safe_name if safe_name.endswith(".md") else f"{safe_name}.md"
        full_path = directory / file_name

        # Avoid collision
        counter = 1
        while full_path.exists():
            full_path = directory / f"{safe_name} {counter}.md"
            counter += 1

        display_name = safe_name.removesuffix(".md")
        content = f"# {display_name}\n\n"
        self.write_note(str(full_path), content)
        return {"path": str(full_path), "content": content, "name": display_name}

    def delete_note(self, file_path: str) -> None:
        Path(file_path).unlink(missing_ok=True)

    def rename_note(self, old_path: str, new_name: str) -> str:
        p = Path(old_path)
        ext = p.suffix or ".md"
        new_name_safe = new_name if new_name.endswith(ext) else f"{new_name}{ext}"
        new_path = p.parent / new_name_safe
        p.rename(new_path)
        return str(new_path)

    def note_exists(self, file_path: str) -> bool:
        return Path(file_path).exists()

    def create_folder(self, name: str, parent_path: Optional[str] = None) -> str:
        parent = Path(parent_path) if parent_path else self.vault_path or Path(".")
        folder = parent / name
        folder.mkdir(parents=True, exist_ok=True)
        return str(folder)

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_all_notes(self) -> list[dict]:
        """Return lightweight stubs for all notes (no content)."""
        if not self.vault_path:
            return []
        stubs = []
        for file_path in self._collect_note_files(self.vault_path):
            try:
                p = Path(file_path)
                content = p.read_text(encoding="utf-8", errors="ignore")
                stat = p.stat()
                stubs.append({
                    "path": file_path,
                    "name": p.stem,
                    "relativePath": str(p.relative_to(self.vault_path)),
                    "content": content,
                    "tags": self._extract_tags(content),
                    "modified": stat.st_mtime,
                })
            except Exception:
                continue
        return stubs

    def _collect_note_files(self, directory: Path) -> list[str]:
        results = []
        try:
            for entry in directory.iterdir():
                if entry.name.startswith("."):
                    continue
                if entry.is_dir():
                    results.extend(self._collect_note_files(entry))
                elif entry.suffix.lower() in NOTE_EXTENSIONS:
                    results.append(str(entry))
        except PermissionError:
            pass
        return results

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _extract_tags(self, content: str) -> list[str]:
        tags = set()
        # YAML frontmatter tags
        fm_match = re.match(r"^---\s*\n([\s\S]*?)\n---", content)
        if fm_match:
            fm = fm_match.group(1)
            inline = re.search(r"tags:\s*\[([^\]]+)\]", fm)
            if inline:
                for t in inline.group(1).split(","):
                    tags.add(t.strip().strip("'\""))
            list_match = re.search(r"tags:\s*\n((?:\s+-\s+.+\n?)+)", fm)
            if list_match:
                for line in list_match.group(1).splitlines():
                    line = line.strip()
                    if line.startswith("-"):
                        tags.add(line[1:].strip())
        # Inline #tags
        for m in TAG_RE.finditer(content):
            tags.add(m.group(1))
        return sorted(tags)

    def _extract_links(self, content: str) -> list[str]:
        return [m.group(1).strip() for m in WIKI_LINK_RE.finditer(content)]

    def resolve_link(self, link_name: str) -> Optional[str]:
        """Resolve a wiki link name to an absolute file path."""
        if not self.vault_path:
            return None
        lower = link_name.lower()
        for file_path in self._collect_note_files(self.vault_path):
            if Path(file_path).stem.lower() == lower:
                return file_path
        return None
