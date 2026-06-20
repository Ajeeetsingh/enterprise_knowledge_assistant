"""Document processor abstraction and default implementation."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from app.documents.types import IngestionContext
from app.ingestion.parsers.factory import ParserFactory, build_default_factory


class DocumentProcessor(ABC):
    """Extract and clean text from a document.

    Concrete implementations encapsulate the full extraction strategy for a
    document family:

    * ``DefaultDocumentProcessor`` — parser-based text extraction + normalization
    * ``OCRDocumentProcessor``    — (future) image-to-text via OCR
    * ``HTMLDocumentProcessor``   — (future) HTML-aware extraction
    * ``MarkdownDocumentProcessor`` — (future) Markdown-aware extraction

    The pipeline depends only on this abstraction; swapping the processor
    requires no stage modifications.
    """

    @abstractmethod
    def process(self, context: IngestionContext) -> str:
        """Extract and clean text from the document in *context*.

        Returns:
            Cleaned plain-text ready for chunking.
        """


class DefaultDocumentProcessor(DocumentProcessor):
    """Parser-based text extraction with whitespace normalization.

    Delegates format-specific parsing to a :class:`ParserFactory`, then
    normalises the returned text so downstream stages receive consistent input.
    """

    def __init__(self, parser_factory: ParserFactory | None = None) -> None:
        self._factory = parser_factory or build_default_factory()

    def process(self, context: IngestionContext) -> str:
        parser = self._factory.get(context.filename)
        raw_text = parser.parse(context.content, context.filename)
        return self._normalize(raw_text)

    @staticmethod
    def _normalize(text: str) -> str:
        """Collapse excess whitespace while preserving paragraph breaks."""
        text = text.strip()
        # Normalise line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse runs of spaces/tabs on each line
        text = "\n".join(" ".join(line.split()) for line in text.split("\n"))
        # Collapse runs of more than two consecutive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text
