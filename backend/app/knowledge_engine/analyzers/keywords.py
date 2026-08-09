"""Keyword extraction analyzer."""

from __future__ import annotations

from app.knowledge_engine.analyzers.base import AnalyzerContext
from app.knowledge_engine.text_utils import top_keywords


class KeywordAnalyzer:
    name = "keywords"

    def __init__(self, *, limit: int = 15) -> None:
        self._limit = limit

    def analyze(self, context: AnalyzerContext) -> None:
        keywords = top_keywords(context.request.text, limit=self._limit)
        # Prefer domain terms already captured as topics when available.
        boosted = list(dict.fromkeys(
            [topic.lower() for topic in context.knowledge.topics[:5]] + keywords
        ))
        context.knowledge.keywords = boosted[: self._limit]
        context.knowledge.confidence.keywords = 0.8 if keywords else 0.25
