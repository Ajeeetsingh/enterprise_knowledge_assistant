"""Document validation stage."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.exceptions import DocumentValidationError
from app.documents.types import IngestionContext
from app.ingestion.stages.base import PipelineStage
from app.ingestion.supported_types import MAX_FILE_SIZE_BYTES, SUPPORTED_EXTENSIONS


class ValidationStage(PipelineStage):
    """Validate incoming document before further processing.

    Built-in checks:
    - Non-empty filename and content
    - Supported file extension
    - File size within limit
    - SHA-256 checksum computation

    The stage is designed for extensibility: future validators (virus scan,
    PII detection, compliance policies) can be added by passing additional
    ``DocumentValidator`` callables to the constructor without modifying
    this class.
    """

    def __init__(
        self,
        max_size_bytes: int = MAX_FILE_SIZE_BYTES,
        extra_validators: list | None = None,
    ) -> None:
        self._max_size_bytes = max_size_bytes
        self._extra_validators = extra_validators or []

    @property
    def name(self) -> str:
        return "validation"

    @property
    def description(self) -> str:
        return "Validate uploaded document before ingestion."

    @property
    def order(self) -> int:
        return 1

    def process(self, context: IngestionContext) -> IngestionContext:
        filename = context.filename.strip()
        if not filename:
            raise DocumentValidationError("Document filename must not be empty.")

        content_type = context.content_type.strip()
        if not content_type:
            raise DocumentValidationError("Document content type must not be empty.")

        if not context.content:
            raise DocumentValidationError("Document content must not be empty.")

        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise DocumentValidationError(
                f"Unsupported file extension '{ext}'. "
                f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
            )

        if len(context.content) > self._max_size_bytes:
            limit_mb = self._max_size_bytes // (1024 * 1024)
            raise DocumentValidationError(
                f"File exceeds the maximum allowed size of {limit_mb} MB."
            )

        context.filename = filename
        context.content_type = content_type
        context.checksum = hashlib.sha256(context.content).hexdigest()

        for validator in self._extra_validators:
            validator.validate(context)

        context.stage_results[self.name] = "validated"
        return context
