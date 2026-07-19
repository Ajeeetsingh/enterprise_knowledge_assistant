"""Unit tests for cross-encoder reranking."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.rag.reranking.config import RerankingSettings
from app.rag.reranking.registry import (
    RerankerRegistryError,
    get_default_spec,
    get_model_spec,
    load_reranker_registry,
)
from app.rag.reranking.reranker import CrossEncoderReranker
from app.rag.reranking.runtime import CrossEncoderRuntime, create_reranker_runtime
from app.rag.reranking.scorer import apply_reranker_scores, score_pairs
from app.rag.reranking.schemas import RerankerMetrics
from app.rag.types import RetrievalResult


def _result(
    chunk_id: str,
    content: str,
    *,
    dense_rank: int | None = None,
    sparse_rank: int | None = None,
    fusion_score: float | None = None,
    metadata_bonus: float | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source="doc.pdf",
        category="general",
        confidence=0.5,
        chunk_id=chunk_id,
        page_number=1,
        dense_rank=dense_rank,
        sparse_rank=sparse_rank,
        fusion_score=fusion_score,
        metadata_bonus=metadata_bonus,
    )


def _settings(**overrides) -> RerankingSettings:
    defaults = {
        "enabled": True,
        "rerank_top_n": 20,
        "rerank_model_id": "ms-marco-minilm-l6-v2",
        "max_batch_size": 8,
        "max_sequence_length": 512,
    }
    defaults.update(overrides)
    return RerankingSettings(**defaults)


class TestRerankerRegistry:
    def test_load_registry_contains_four_models(self) -> None:
        specs = load_reranker_registry()
        assert len(specs) == 4
        assert {spec.id for spec in specs} == {
            "ms-marco-minilm-l6-v2",
            "ms-marco-minilm-l12-v2",
            "bge-reranker-base",
            "bge-reranker-large",
        }

    def test_get_model_spec_by_id(self) -> None:
        spec = get_model_spec("bge-reranker-base")
        assert spec.model_name == "BAAI/bge-reranker-base"

    def test_get_default_spec(self) -> None:
        spec = get_default_spec()
        assert spec.is_default is True
        assert spec.id == "ms-marco-minilm-l6-v2"

    def test_unknown_model_raises(self) -> None:
        with pytest.raises(RerankerRegistryError, match="Unknown reranker model id"):
            get_model_spec("does-not-exist")


class TestCrossEncoderRuntime:
    def test_device_cpu_when_cuda_unavailable(self) -> None:
        runtime = create_reranker_runtime(_settings())
        assert runtime.device == "cpu"

    def test_device_cuda_when_available(self) -> None:
        with patch("app.rag.reranking.runtime._resolve_device", return_value="cuda"):
            runtime = create_reranker_runtime(_settings())
            assert runtime.device == "cuda"

    def test_batch_predict_uses_configured_batch_size(self) -> None:
        runtime = CrossEncoderRuntime(
            get_model_spec("ms-marco-minilm-l6-v2"),
            settings=_settings(max_batch_size=4),
        )
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.1, 0.9, 0.5]
        runtime._model = mock_model

        outcome = score_pairs(
            runtime,
            query="What is the CEO name?",
            passages=["David Chen", "Quarterly revenue", "Singapore HQ"],
            settings=_settings(max_batch_size=4),
        )

        mock_model.predict.assert_called_once()
        _, kwargs = mock_model.predict.call_args
        assert kwargs["batch_size"] == 4
        assert outcome.scores == [0.1, 0.9, 0.5]
        assert outcome.metrics.candidates_reranked == 3


class TestApplyRerankerScores:
    def test_sorts_by_reranker_score_descending(self) -> None:
        results = [
            _result("a", "alpha"),
            _result("b", "beta"),
            _result("c", "gamma"),
        ]
        reranked = apply_reranker_scores(results, [0.2, 0.9, 0.5])
        assert [item.chunk_id for item in reranked] == ["b", "c", "a"]
        assert reranked[0].final_rank == 1
        assert reranked[0].reranker_score == 0.9

    def test_deterministic_tie_break_by_chunk_id(self) -> None:
        results = [
            _result("b", "beta"),
            _result("a", "alpha"),
        ]
        first = apply_reranker_scores(results, [0.5, 0.5])
        second = apply_reranker_scores(results, [0.5, 0.5])
        assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
        assert first[0].chunk_id == "a"

    def test_metadata_bonus_weight_zero_matches_prior_behavior(self) -> None:
        """Default (weight=0) blending must reproduce the original raw-score
        ranking exactly — this is the backward-compatibility guard for the
        metadata-aware reranking fix."""
        results = [
            _result("a", "alpha", metadata_bonus=0.15),
            _result("b", "beta", metadata_bonus=0.0),
            _result("c", "gamma", metadata_bonus=0.1),
        ]
        reranked = apply_reranker_scores(results, [0.2, 0.9, 0.5])
        assert [item.chunk_id for item in reranked] == ["b", "c", "a"]
        assert reranked[0].final_score == reranked[0].reranker_score == 0.9

    def test_metadata_bonus_breaks_close_cross_encoder_tie(self) -> None:
        """When the cross-encoder is nearly undecided between two closely
        related chunks in a larger candidate pool, a meaningfully stronger
        metadata/heading bonus should be able to flip their *relative*
        order — this is the "metadata-aware reranking" fix for cases like
        issuers vs. investors sections. (A 2-item pool is avoided here
        because min-max normalization degenerates to a hard 0/1 split for
        exactly two scores, which isn't representative of a real rerank
        pool of ~20 candidates.)"""
        results = [
            _result("distractor_high", "unrelated but strong match", metadata_bonus=0.0),
            _result("investors", "investors body", metadata_bonus=0.02),
            _result("issuers", "issuers body", metadata_bonus=0.12),
            _result("distractor_low", "unrelated weak match", metadata_bonus=0.0),
        ]
        # Cross-encoder scores are close for investors/issuers (investors
        # slightly ahead) — a realistic model-confusion scenario.
        reranked = apply_reranker_scores(
            results,
            [0.95, 0.60, 0.58, 0.10],
            metadata_bonus_weight=0.3,
            metadata_bonus_reference=0.15,
        )
        ranked_ids = [item.chunk_id for item in reranked]
        assert ranked_ids.index("issuers") < ranked_ids.index("investors")

    def test_metadata_bonus_does_not_override_decisive_cross_encoder_gap(self) -> None:
        """A small metadata bonus must not overturn a clearly decisive
        cross-encoder preference — the model remains the dominant signal."""
        results = [
            _result("weak_heading_strong_match", "content", metadata_bonus=0.15),
            _result("no_heading_best_match", "content", metadata_bonus=0.0),
        ]
        reranked = apply_reranker_scores(
            results,
            [0.05, 0.98],
            metadata_bonus_weight=0.3,
            metadata_bonus_reference=0.15,
        )
        assert reranked[0].chunk_id == "no_heading_best_match"

    def test_explainability_fields_present(self) -> None:
        result = _result(
            "x",
            "content",
            dense_rank=6,
            sparse_rank=2,
            fusion_score=0.042,
            metadata_bonus=0.07,
        )
        reranked = apply_reranker_scores([result], [0.962])
        explanation = "\n".join(reranked[0].score_explanation or [])
        assert "Dense Rank      6" in explanation
        assert "Sparse Rank     2" in explanation
        assert "Fusion Score    0.042" in explanation
        assert "Metadata Bonus  +0.07" in explanation
        assert "Reranker Score  0.962" in explanation
        assert "Final Rank      1" in explanation


class TestCrossEncoderReranker:
    def test_disabled_returns_top_k_without_scoring(self) -> None:
        reranker = CrossEncoderReranker(settings=_settings(enabled=False))
        candidates = [_result("a", "alpha"), _result("b", "beta")]
        output = reranker.rerank("query", candidates, top_k=1)
        assert len(output) == 1
        assert output[0].chunk_id == "a"
        assert output[0].reranker_score is None

    def test_rerank_returns_top_k_after_sorting(self) -> None:
        runtime = MagicMock()
        runtime.spec.id = "ms-marco-minilm-l6-v2"
        runtime.model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        runtime.device = "cpu"
        runtime.get_model.return_value.predict.return_value = [0.1, 0.95, 0.4]

        reranker = CrossEncoderReranker(
            settings=_settings(rerank_top_n=3),
            runtime=runtime,
        )
        candidates = [
            _result("a", "alpha"),
            _result("b", "beta"),
            _result("c", "gamma"),
            _result("d", "delta"),
        ]
        output = reranker.rerank("query", candidates, top_k=2)
        assert len(output) == 2
        assert output[0].chunk_id == "b"
        assert output[0].reranker_score == 0.95

    def test_fallback_on_scoring_failure(self) -> None:
        runtime = MagicMock()
        runtime.spec.id = "ms-marco-minilm-l6-v2"
        runtime.model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        runtime.device = "cpu"
        runtime.get_model.return_value.predict.side_effect = RuntimeError("model failed")

        reranker = CrossEncoderReranker(settings=_settings(), runtime=runtime)
        candidates = [_result("a", "alpha"), _result("b", "beta")]
        output = reranker.rerank("query", candidates, top_k=2)
        assert [item.chunk_id for item in output] == ["a", "b"]
        assert output[0].reranker_score is None

    def test_configuration_from_settings(self, monkeypatch) -> None:
        from app.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RERANK_TOP_N", "12")
        monkeypatch.setenv("RERANK_MODEL", "bge-reranker-base")
        monkeypatch.setenv("RERANK_MAX_BATCH_SIZE", "32")

        resolved = RerankingSettings.from_settings()
        assert resolved.rerank_top_n == 12
        assert resolved.rerank_model_id == "bge-reranker-base"
        assert resolved.max_batch_size == 32
        get_settings.cache_clear()


class TestEngineRerankingIntegration:
    def test_search_passes_rerank_top_n_to_hybrid_and_reranks(self, monkeypatch) -> None:
        from app.rag.engine import EnterpriseRAG
        from app.rag.hybrid.config import HybridRetrievalSettings

        faiss_store = MagicMock()
        faiss_store.size = 10
        hybrid_hit = _result("a", "alpha")
        reranked_hit = _result("b", "beta", dense_rank=2)
        reranked_hit.reranker_score = 0.99
        reranked_hit.final_rank = 1

        hybrid_retriever = MagicMock()
        hybrid_retriever.search.return_value = [hybrid_hit, _result("b", "beta")]

        reranker = MagicMock()
        reranker.runtime = MagicMock()
        reranker.rerank.return_value = [reranked_hit]

        query_processor = MagicMock()
        query_processor.process.return_value = MagicMock(
            original_query="CEO name",
            expanded_query="CEO name",
            retrieval_queries=("CEO name",),
            strategy=MagicMock(
                name="entity_lookup",
                sparse_weight=1.25,
                dense_weight=0.9,
                metadata_bonus_multiplier=1.0,
                rerank_top_n=20,
                retrieval_depth_multiplier=0.85,
            ),
            classification=MagicMock(category=MagicMock(value="entity_lookup")),
            detected_entities=(),
        )

        monkeypatch.setattr("app.rag.engine.HybridRetriever", lambda **kwargs: hybrid_retriever)
        monkeypatch.setattr("app.rag.engine.MetadataAwareRetriever", lambda **kwargs: MagicMock())
        monkeypatch.setattr("app.rag.engine.CrossEncoderReranker", lambda **kwargs: reranker)

        engine = EnterpriseRAG(
            vector_store=faiss_store,
            hybrid_settings=HybridRetrievalSettings(enabled=True),
            reranking_settings=_settings(enabled=True, rerank_top_n=20),
            hybrid_retriever=hybrid_retriever,
            reranker=reranker,
            query_processor=query_processor,
        )
        engine._standalone_bm25 = MagicMock()

        results = engine._search(
            "CEO name",
            top_k=5,
            allowed_categories={"general"},
            authorized_sources=None,
        )

        hybrid_retriever.search.assert_called_once()
        assert hybrid_retriever.search.call_args.kwargs["top_k"] == 20
        reranker.rerank.assert_called_once()
        assert results[0].chunk_id == "b"
