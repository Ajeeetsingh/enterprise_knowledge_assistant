"""Document processor abstraction and default implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.documents.types import IngestionContext
from app.ingestion.normalization import CanonicalNormalizer
from app.ingestion.normalization.config import NormalizationSettings
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

    def __init__(
        self,
        parser_factory: ParserFactory | None = None,
        normalizer: CanonicalNormalizer | None = None,
    ) -> None:
        self._factory = parser_factory or build_default_factory()
        self._normalizer = normalizer or CanonicalNormalizer(
            settings=NormalizationSettings.from_settings()
        )

    def process(self, context: IngestionContext) -> str:
        parser = self._factory.get(context.filename)
        raw_text = parser.parse(context.content, context.filename)
        return self._normalize(raw_text)

    def _normalize(self, text: str) -> str:
        """Run canonical normalization before chunking."""
        return self._normalizer.normalize(text)

    @staticmethod
    def normalize_text(
        text: str,
        settings: NormalizationSettings | None = None,
    ) -> str:
        """Normalize text without parser extraction (scripts and evaluation helpers)."""
        normalizer = CanonicalNormalizer(settings=settings or NormalizationSettings.from_settings())
        return normalizer.normalize(text)

    def extract_structure(
        self,
        text: str,
        source: str,
    ):
        """Extract hierarchical document structure from normalized text."""
        from app.ingestion.structure.extractor import StructureExtractor

        extractor = StructureExtractor()
        return extractor.extract(text, source)
