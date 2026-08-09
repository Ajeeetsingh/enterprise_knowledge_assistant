"""Aggregate confidence scoring analyzer."""

from __future__ import annotations

from app.knowledge_engine.analyzers.base import AnalyzerContext


class ConfidenceAnalyzer:
    name = "confidence"

    def analyze(self, context: AnalyzerContext) -> None:
        conf = context.knowledge.confidence
        parts = [
            conf.document_type,
            conf.departments,
            conf.topics,
            conf.keywords,
            conf.entities,
            conf.summary,
            conf.tags,
        ]
        present = [value for value in parts if value > 0]
        conf.overall = round(sum(present) / len(present), 3) if present else 0.0
