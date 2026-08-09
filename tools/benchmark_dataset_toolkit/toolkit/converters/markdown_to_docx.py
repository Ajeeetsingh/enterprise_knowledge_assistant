"""Future: Markdown → DOCX converter (not implemented yet).

Register a concrete subclass of BaseConverter here and add it to
``get_default_registry()`` when the DOCX pipeline is built.
"""

from __future__ import annotations

from typing import ClassVar

from toolkit.converters.base import BaseConverter, ConverterContext
from toolkit.models import ConversionJob, ConversionResult


class MarkdownToDocxConverter(BaseConverter):
    """Placeholder for the DOCX pipeline."""

    name: ClassVar[str] = "markdown_to_docx"
    description: ClassVar[str] = "Convert Markdown to DOCX via Pandoc (planned)"
    target_suffix: ClassVar[str] = ".docx"

    def convert_one(self, job: ConversionJob, context: ConverterContext) -> ConversionResult:
        raise NotImplementedError(
            "markdown_to_docx is not implemented yet. "
            "See README.md roadmap in tools/benchmark_dataset_toolkit/."
        )
