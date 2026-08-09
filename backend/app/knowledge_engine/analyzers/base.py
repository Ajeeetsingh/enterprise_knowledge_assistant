"""Analyzer contracts for the Knowledge Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.knowledge_engine.types import DocumentKnowledge, KnowledgeAnalysisRequest


@dataclass
class AnalyzerContext:
    """Shared mutable context passed through the analyzer chain."""

    request: KnowledgeAnalysisRequest
    knowledge: DocumentKnowledge
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class KnowledgeAnalyzer(Protocol):
    """Single-responsibility analyzer that mutates ``AnalyzerContext.knowledge``."""

    name: str

    def analyze(self, context: AnalyzerContext) -> None:
        """Enrich the knowledge object. Must not raise into the pipeline."""
        ...
