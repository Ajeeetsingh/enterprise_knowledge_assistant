"""Heuristic AI summary analyzer (LLM enrichment is optional and fail-open)."""

from __future__ import annotations

from app.knowledge_engine.analyzers.base import AnalyzerContext
from app.knowledge_engine.text_utils import first_nonempty_lines, split_sentences
from app.knowledge_engine.types import SummaryBlock


class SummaryAnalyzer:
    name = "summary"

    def __init__(self, *, short_sentence_limit: int = 2, detailed_sentence_limit: int = 8) -> None:
        self._short_limit = short_sentence_limit
        self._detailed_limit = detailed_sentence_limit

    def analyze(self, context: AnalyzerContext) -> None:
        text = context.request.text.strip()
        if not text:
            context.knowledge.summary = SummaryBlock(
                short="No extractable text was available for summarization.",
                detailed="No extractable text was available for summarization.",
            )
            context.warnings.append("summary: empty source text")
            context.knowledge.confidence.summary = 0.1
            return

        sentences = split_sentences(text)
        if not sentences:
            lines = first_nonempty_lines(text, limit=self._detailed_limit)
            short = " ".join(lines[: self._short_limit]).strip()
            detailed = " ".join(lines).strip()
        else:
            short = " ".join(sentences[: self._short_limit]).strip()
            detailed = " ".join(sentences[: self._detailed_limit]).strip()

        # Prefer a title-like first line when it looks like a document header.
        headers = first_nonempty_lines(text, limit=2)
        if headers and len(headers[0]) <= 120 and headers[0].isupper():
            short = f"{headers[0].title()}. {short}".strip()

        context.knowledge.summary = SummaryBlock(
            short=short[:500],
            detailed=detailed[:2500],
        )
        context.knowledge.confidence.summary = 0.72 if len(sentences) >= 2 else 0.55
