"""Knowledge Engine orchestrator (Phase 13.1)."""

from __future__ import annotations

import logging
import time
from typing import Sequence

from app.core.logging import get_logger, log_with_fields
from app.knowledge_engine.analyzers import (
    ConfidenceAnalyzer,
    DepartmentAnalyzer,
    DocumentTypeAnalyzer,
    EntityAnalyzer,
    KeywordAnalyzer,
    KnowledgeAnalyzer,
    MetadataAnalyzer,
    SummaryAnalyzer,
    TagAnalyzer,
    TopicAnalyzer,
)
from app.knowledge_engine.analyzers.base import AnalyzerContext
from app.knowledge_engine.enums import KnowledgeProcessingStatus
from app.knowledge_engine.types import DocumentKnowledge, KnowledgeAnalysisRequest, ProcessingInfo
from app.knowledge_engine.version import PIPELINE_VERSION

logger = get_logger(__name__)


def default_analyzers() -> list[KnowledgeAnalyzer]:
    """Return the ordered Phase 13.1 analyzer chain (SOLID: open for extension)."""
    return [
        MetadataAnalyzer(),
        SummaryAnalyzer(),
        DocumentTypeAnalyzer(),
        DepartmentAnalyzer(),
        TopicAnalyzer(),
        KeywordAnalyzer(),
        EntityAnalyzer(),
        TagAnalyzer(),
        ConfidenceAnalyzer(),
    ]


class KnowledgeEngine:
    """Transform document text into a canonical ``DocumentKnowledge`` object.

    Completely independent of the legacy RAG/ingestion retrieval path.
    """

    def __init__(
        self,
        analyzers: Sequence[KnowledgeAnalyzer] | None = None,
        *,
        model_used: str = "heuristic-v1",
    ) -> None:
        self._analyzers = list(analyzers) if analyzers is not None else default_analyzers()
        self._model_used = model_used

    def analyze(self, request: KnowledgeAnalysisRequest) -> DocumentKnowledge:
        """Run all analyzers and return a fully populated Knowledge Object."""
        started = time.perf_counter()
        knowledge = DocumentKnowledge(document_id=request.document_id)
        context = AnalyzerContext(request=request, knowledge=knowledge)

        for analyzer in self._analyzers:
            try:
                analyzer.analyze(context)
            except Exception as exc:  # noqa: BLE001 — shadow path must never raise
                message = f"{analyzer.name}: {type(exc).__name__}: {exc}"
                context.errors.append(message)
                log_with_fields(
                    logger,
                    logging.WARNING,
                    "Knowledge analyzer failed",
                    analyzer=analyzer.name,
                    document_id=request.document_id,
                    reason=type(exc).__name__,
                )

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        if context.errors and (
            not knowledge.summary.short
            and knowledge.document_type == "Unknown"
            and not knowledge.keywords
        ):
            status = KnowledgeProcessingStatus.FAILED
        elif context.errors or context.warnings:
            status = KnowledgeProcessingStatus.PARTIAL
        else:
            status = KnowledgeProcessingStatus.SUCCESS

        knowledge.processing_info = ProcessingInfo(
            processing_time_ms=elapsed_ms,
            pipeline_version=PIPELINE_VERSION,
            model_used=self._model_used,
            warnings=list(context.warnings),
            errors=list(context.errors),
            status=status.value,
        )
        return knowledge
