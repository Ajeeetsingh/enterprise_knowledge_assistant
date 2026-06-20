"""Plain-text document parser."""

from __future__ import annotations

from app.ingestion.parsers.base import DocumentParser


class TxtParser(DocumentParser):
    """Parse UTF-8 plain-text files."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".txt"})

    def parse(self, content: bytes, filename: str) -> str:
        return content.decode("utf-8", errors="replace")
