"""Unit tests for reranker confidence calibration."""

from __future__ import annotations

from app.rag.reranking.scorer import apply_reranker_scores, _reranker_display_confidence
from app.rag.types import RetrievalResult, calibrate_confidence


def _result(*, raw_cosine: float | None = None) -> RetrievalResult:
    return RetrievalResult(
        content="Executive leadership table",
        source="GTFS-EXEC-001_Company_Overview.pdf",
        category="executive",
        confidence=0.5,
        chunk_id="exec-1",
        raw_cosine_score=raw_cosine,
    )


class TestRerankerDisplayConfidence:
    def test_uses_calibrated_cosine_when_available(self) -> None:
        result = _result(raw_cosine=0.36)
        confidence = _reranker_display_confidence(result, raw_reranker_score=9.5)
        assert confidence == calibrate_confidence(0.36)
        assert confidence < 1.0

    def test_does_not_inflate_top_hit_to_one(self) -> None:
        reranked = apply_reranker_scores([_result(raw_cosine=0.36)], [9.5])
        assert reranked[0].confidence < 1.0
        assert reranked[0].confidence == calibrate_confidence(0.36)

    def test_sigmoid_fallback_without_cosine(self) -> None:
        result = _result(raw_cosine=None)
        confidence = _reranker_display_confidence(result, raw_reranker_score=-4.0)
        assert 0.0 < confidence < 0.5
