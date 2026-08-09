"""Failure policy — log, continue, partial evidence, never fail production."""

from __future__ import annotations

import logging

from app.core.logging import get_logger, log_with_fields
from app.knowledge_orchestration.models.types import WorkerEvidence

logger = get_logger(__name__)


class FailurePolicy:
    def handle(self, evidence: WorkerEvidence) -> WorkerEvidence:
        if evidence.success and not evidence.timed_out and not evidence.skipped:
            return evidence
        log_with_fields(
            logger,
            logging.WARNING,
            "Orchestration worker soft-failed",
            worker_id=evidence.worker_id,
            error=evidence.error,
            timed_out=evidence.timed_out,
            skipped=evidence.skipped,
        )
        # Continue with partial evidence (may be empty).
        return evidence
