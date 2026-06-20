"""DOCX document parser."""

from __future__ import annotations

from app.core.exceptions import DocumentIngestionError
from app.ingestion.parsers.base import DocumentParser


class DocxParser(DocumentParser):
    """Extract text from Word .docx files using python-docx."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".docx"})

    def parse(self, content: bytes, filename: str) -> str:
        try:
            import docx
        except ImportError as exc:
            raise DocumentIngestionError(
                "python-docx is required for DOCX parsing. "
                "Install it with: pip install python-docx"
            ) from exc

        import io

        doc = docx.Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
