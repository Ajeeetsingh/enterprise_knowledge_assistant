"""Parser registry and factory."""

from __future__ import annotations

from pathlib import Path

from app.core.exceptions import ParserNotFoundError
from app.ingestion.parsers.base import DocumentParser


class ParserFactory:
    """Registry that maps file extensions to ``DocumentParser`` implementations.

    Registration pattern keeps the pipeline open for extension and closed for
    modification: adding a new format requires only one ``register()`` call.
    """

    def __init__(self) -> None:
        self._registry: dict[str, DocumentParser] = {}

    def register(self, parser: DocumentParser) -> None:
        """Register a parser for all extensions it declares."""
        for ext in parser.supported_extensions:
            self._registry[ext.lower()] = parser

    def get(self, filename: str) -> DocumentParser:
        """Return the parser for the given filename's extension.

        Raises:
            ParserNotFoundError: If no parser is registered for the extension.
        """
        ext = Path(filename).suffix.lower()
        parser = self._registry.get(ext)
        if parser is None:
            raise ParserNotFoundError(
                f"No parser registered for extension '{ext}'. "
                f"Supported: {sorted(self._registry)}"
            )
        return parser

    def supported_extensions(self) -> frozenset[str]:
        """Return all currently registered extensions."""
        return frozenset(self._registry)


def build_default_factory() -> ParserFactory:
    """Build a ``ParserFactory`` pre-loaded with all MVP parsers."""
    from app.ingestion.parsers.csv import CsvParser
    from app.ingestion.parsers.docx import DocxParser
    from app.ingestion.parsers.json import JsonParser
    from app.ingestion.parsers.pdf import PdfParser
    from app.ingestion.parsers.txt import TxtParser
    from app.ingestion.parsers.xlsx import XlsxParser

    factory = ParserFactory()
    for parser in (
        TxtParser(),
        CsvParser(),
        JsonParser(),
        PdfParser(),
        DocxParser(),
        XlsxParser(),
    ):
        factory.register(parser)
    return factory
