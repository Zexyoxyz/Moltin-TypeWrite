# -- Path bootstrap ------------------------------------------------------------
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# -----------------------------------------------------------------------------
"""
SearchService — fuzzy full-text search across all notes using rapidfuzz.
Index is rebuilt on vault open and after file changes.
"""

from rapidfuzz import fuzz, process
from typing import Optional
from services.file_service import FileService


class SearchService:
    def __init__(self, file_service: FileService):
        self.file_service = file_service
        self._index: list[dict] = []  # list of note stubs with content

    def rebuild_index(self) -> int:
        """Rebuild search index from vault. Returns number of indexed notes."""
        self._index = self.file_service.index_all_notes()
        return len(self._index)

    def search(self, query: str, limit: int = 50) -> list[dict]:
        """Full fuzzy search across titles and content."""
        if not query.strip() or not self._index:
            return []

        query_lower = query.lower()
        results = []

        for note in self._index:
            title_score = fuzz.partial_ratio(query_lower, note["name"].lower())
            content_score = fuzz.partial_ratio(query_lower, note["content"][:5000].lower())
            # Weighted: title matters more
            combined = (title_score * 0.6) + (content_score * 0.4)

            if combined > 35:
                # Extract a relevant snippet
                snippet = self._find_snippet(query_lower, note["content"])
                results.append({
                    "path": note["path"],
                    "name": note["name"],
                    "relativePath": note["relativePath"],
                    "score": combined,
                    "snippet": snippet,
                    "tags": note.get("tags", []),
                })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]

    def search_titles(self, query: str, limit: int = 20) -> list[dict]:
        """Quick title-only search for the quick switcher (Ctrl+P)."""
        if not query.strip() or not self._index:
            return []
        query_lower = query.lower()
        scored = [
            (note, fuzz.partial_ratio(query_lower, note["name"].lower()))
            for note in self._index
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "path": n["path"],
                "name": n["name"],
                "relativePath": n["relativePath"],
                "score": s,
            }
            for n, s in scored
            if s > 30
        ][:limit]

    def _find_snippet(self, query: str, content: str, context: int = 120) -> str:
        """Find a relevant snippet of text around the query match."""
        lower_content = content.lower()
        idx = lower_content.find(query)
        if idx == -1:
            # Try first word
            first_word = query.split()[0] if query.split() else query
            idx = lower_content.find(first_word)
        if idx == -1:
            return content[:context].strip()

        start = max(0, idx - 40)
        end = min(len(content), idx + context)
        snippet = content[start:end].strip()
        if start > 0:
            snippet = "…" + snippet
        if end < len(content):
            snippet = snippet + "…"
        return snippet

    def get_index_size(self) -> int:
        return len(self._index)
