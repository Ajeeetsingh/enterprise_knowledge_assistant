"""Re-extract document text for shadow-mode analysis.

Reuses the existing parser factory without modifying the ingestion pipeline.
"""

from __future__ import annotations

from app.ingestion.parsers import build_default_factory


def extract_text_from_bytes(filename: str, content: bytes) -> str:
    """Return plain text extracted from *content* using registered parsers."""
    factory = build_default_factory()
    parser = factory.get(filename)
    return parser.parse(content, filename) or ""
