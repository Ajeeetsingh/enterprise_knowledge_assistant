"""Abstract converter interface — extend for DOCX, OCR, scanned PDF, etc."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from toolkit.config import ToolkitConfig
from toolkit.models import ConversionJob, ConversionResult


@dataclass(slots=True)
class ConverterContext:
    """Runtime knobs passed into each converter invocation."""

    config: ToolkitConfig
    force: bool = False
    dry_run: bool = False
    verbose: bool = False


class BaseConverter(ABC):
    """Strategy interface for a single artefact pipeline.

    Future converters (DOCX, scanned PDF, OCR sets) subclass this and
    register themselves with :class:`ConverterRegistry` — no changes to
    the pipeline orchestrator are required.
    """

    name: ClassVar[str]
    description: ClassVar[str] = ""
    source_suffix: ClassVar[str] = ".md"
    target_suffix: ClassVar[str] = ".pdf"

    @abstractmethod
    def convert_one(self, job: ConversionJob, context: ConverterContext) -> ConversionResult:
        """Convert a single job. Must not raise for expected conversion failures;
        return a FAILED :class:`ConversionResult` instead when continue_on_error
        semantics are desired by the caller.
        """

    def build_jobs(self, config: ToolkitConfig) -> list[ConversionJob]:
        """Default job builder — subclasses may override for non-MD sources."""
        from toolkit.discovery import build_jobs

        return build_jobs(config)

    def verify_target(self, path: Path, context: ConverterContext) -> bool:
        """Optional post-condition check; default is existence + non-empty."""
        try:
            return path.is_file() and path.stat().st_size > 0
        except OSError:
            return False
