"""Shared domain models for conversion jobs and reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ConversionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DRY_RUN = "dry_run"


@dataclass(frozen=True, slots=True)
class ConversionJob:
    """One markdown source → target artefact mapping."""

    source: Path
    target: Path
    relative_source: Path


@dataclass(slots=True)
class ConversionResult:
    job: ConversionJob
    status: ConversionStatus
    elapsed_seconds: float = 0.0
    error: str | None = None
    verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": str(self.job.source),
            "target": str(self.job.target),
            "relative_source": str(self.job.relative_source).replace("\\", "/"),
            "status": self.status.value,
            "elapsed_seconds": round(self.elapsed_seconds, 4),
            "error": self.error,
            "verified": self.verified,
        }


@dataclass(slots=True)
class ConversionReport:
    """Aggregate metrics written to conversion_report.json."""

    toolkit: str
    converter: str
    input_dir: str
    output_dir: str
    total_files: int
    success: int
    failed: int
    skipped: int
    dry_run: int
    elapsed_seconds: float
    average_conversion_seconds: float
    workers: int
    force: bool
    dry_run_mode: bool
    verified_ok: int
    verified_failed: int
    errors: list[dict[str, Any]] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
