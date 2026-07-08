"""PDF document parser with per-page text extraction."""

from __future__ import annotations

from app.core.exceptions import DocumentIngestionError
from app.ingestion.parsers.base import DocumentParser

# Each page in extracted text is prefixed with this marker so the chunker
# can track page numbers without breaking the plain-text pipeline.
PAGE_MARKER_TEMPLATE = "<<<PAGE:{page}>>>"


class PdfParser(DocumentParser):
    """Extract text from PDF files using pypdf, preserving page boundaries."""

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
        page_blocks: list[str] = []

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                marker = PAGE_MARKER_TEMPLATE.format(page=page_number)
                page_blocks.append(f"{marker}\n{text.strip()}")

        return "\n".join(page_blocks)
