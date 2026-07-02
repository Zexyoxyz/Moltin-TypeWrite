# -- Path bootstrap ------------------------------------------------------------
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# -----------------------------------------------------------------------------
"""
BacklinkService — builds and queries the wiki-link graph.
Maintains forward links and backlinks for all notes.
"""

import re
from pathlib import Path
from services.file_service import FileService

WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


class BacklinkService:
    def __init__(self, file_service: FileService):
        self.file_service = file_service
        # note_name.lower() → list of backlink entries
        self._backlinks: dict[str, list[dict]] = {}
        # file_path → list of linked note names
        self._forward_links: dict[str, list[str]] = {}

    def build_index(self) -> None:
        """Rebuild the full backlink graph from all notes in the vault."""
        self._backlinks.clear()
        self._forward_links.clear()

        for note in self.file_service.index_all_notes():
            links_with_ctx = self._extract_links_with_context(note["content"])
            self._forward_links[note["path"]] = [l["target"] for l in links_with_ctx]

            for link in links_with_ctx:
                target = link["target"].lower()
                if target not in self._backlinks:
                    self._backlinks[target] = []
                self._backlinks[target].append({
                    "sourcePath": note["path"],
                    "sourceName": note["name"],
                    "context": link["context"],
                })

    def get_backlinks(self, note_name: str) -> list[dict]:
        """Return all notes that link to the given note (by name)."""
        normalized = note_name.lower().removesuffix(".md")
        return self._backlinks.get(normalized, [])

    def get_forward_links(self, file_path: str) -> list[str]:
        """Return all wiki links in a given note."""
        return self._forward_links.get(file_path, [])

    def get_link_graph(self) -> dict[str, list[str]]:
        """Return the full adjacency list for the graph view."""
        return dict(self._forward_links)

    def _extract_links_with_context(self, content: str) -> list[dict]:
        results = []
        for line in content.splitlines():
            for m in WIKI_LINK_RE.finditer(line):
                results.append({
                    "target": m.group(1).strip(),
                    "context": line.strip()[:120],
                })
        return results
