"""PDF document parser."""

from __future__ import annotations

from app.core.exceptions import DocumentIngestionError
from app.ingestion.parsers.base import DocumentParser


class PdfParser(DocumentParser):
    """Extract text from PDF files using pypdf."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".pdf"})

    def parse(self, content: bytes, filename: str) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise DocumentIngestionError(
                "pypdf is required for PDF parsing. Install it with: pip install pypdf"
            ) from exc

        import io

        reader = PdfReader(io.BytesIO(content))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        return "\n".join(pages)
