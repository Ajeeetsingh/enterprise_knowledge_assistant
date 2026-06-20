"""Document parser interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class DocumentParser(ABC):
    """Extract plain text from a specific document format.

    Concrete implementations handle one format each.  Adding support for
    a new format requires only a new ``DocumentParser`` subclass and one
    registration call on ``ParserFactory`` — no pipeline changes.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> frozenset[str]:
        """File extensions this parser handles, e.g. ``{'.txt'}``."""

    @abstractmethod
    def parse(self, content: bytes, filename: str) -> str:
        """Extract plain text from raw document bytes.

        Args:
            content: Raw file bytes.
            filename: Original filename (used for format hints and error messages).

        Returns:
            Extracted plain-text content (may be empty for blank documents).
        """
