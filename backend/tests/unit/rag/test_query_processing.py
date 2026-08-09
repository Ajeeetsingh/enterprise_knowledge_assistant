"""Unit tests for query intelligence processing."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.rag.hybrid.config import HybridRetrievalSettings
from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
from app.rag.query_processing.acronyms import expand_acronyms
from app.rag.query_processing.classifier import classify_query
from app.rag.query_processing.config import QueryProcessingSettings
from app.rag.query_processing.entities import detect_entities, normalize_entities
from app.rag.query_processing.expander import expand_query, generate_retrieval_queries
from app.rag.query_processing.multi_query import merge_multi_query_results
from app.rag.query_processing.processor import QueryProcessor
from app.rag.query_processing.registry import get_rules, load_query_rules
from app.rag.query_processing.schemas import QueryCategory
from app.rag.query_processing.strategy import (
    apply_strategy_to_hybrid_settings,
    select_strategy,
)
from app.rag.query_processing.synonyms import expand_synonyms
from app.rag.reranking.config import RerankingSettings
from app.rag.types import RetrievalResult


def _settings(**overrides) -> QueryProcessingSettings:
    defaults = {
        "enabled": True,
        "query_expansion_enabled": True,
        "multi_query_enabled": True,
        "max_generated_queries": 4,
        "entity_normalization_enabled": True,
        "synonym_expansion_enabled": True,
        "strategy_selection_enabled": True,
    }
    defaults.update(overrides)
    return QueryProcessingSettings(**defaults)


def _result(chunk_id: str, *, score: float) -> RetrievalResult:
    return RetrievalResult(
        content=f"content-{chunk_id}",
        source="doc.pdf",
        category="general",
        confidence=score,
        chunk_id=chunk_id,
        final_score=score,
    )


class TestRegistry:
    def test_load_rules_contains_acronyms_entities_strategies(self) -> None:
        rules = load_query_rules()
        assert "HQ" in rules.acronyms
        assert "CEO" in rules.entities
        assert "financial" in rules.strategies


class TestClassification:
    def test_classifies_entity_lookup(self) -> None:
        result = classify_query("Who is the CEO?")
        assert result.category == QueryCategory.ENTITY_LOOKUP

    def test_classifies_financial(self) -> None:
        result = classify_query("What was quarterly revenue in Q1?")
        assert result.category == QueryCategory.FINANCIAL

    def test_classifies_cross_document(self) -> None:
        result = classify_query("What related GTFS document is referenced?")
        assert result.category == QueryCategory.CROSS_DOCUMENT

    def test_classifies_security(self) -> None:
        result = classify_query("What are the VPN security requirements?")
        assert result.category == QueryCategory.SECURITY


class TestExpansion:
    def test_acronym_expansion_keeps_original_term(self) -> None:
        rules = get_rules()
        expanded, applied = expand_acronyms("What is HQ?", rules)
        assert "HQ" in expanded
        assert "headquarters" in expanded.lower()
        assert applied

    def test_synonym_expansion_appends_related_terms(self) -> None:
        rules = get_rules()
        expanded, applied = expand_synonyms("company headquarters", rules)
        assert "headquarters" in expanded.lower()
        assert any("office" in item or "location" in item for item in expanded.lower().split())
        assert applied

    def test_entity_normalization_replaces_alias(self) -> None:
        rules = get_rules()
        normalized, detected, applied = normalize_entities("Who is the ceo?", rules)
        assert "Chief Executive Officer" in normalized
        assert "CEO" in detected
        assert applied

    def test_entity_detection_for_project_phoenix(self) -> None:
        rules = get_rules()
        detected = detect_entities("What is Project Phoenix?", rules)
        assert "Project Phoenix" in detected


class TestMultiQuery:
    def test_generates_multiple_queries_for_headquarters(self) -> None:
        rules = get_rules()
        classification = classify_query("What is the headquarters?")
        normalized, expanded, detected, _ = expand_query(
            "What is the headquarters?",
            registry=rules,
            settings=_settings(),
        )
        queries = generate_retrieval_queries(
            original_query="What is the headquarters?",
            normalized_query=normalized,
            expanded_query=expanded,
            classification=classification,
            detected_entities=detected,
            registry=rules,
            settings=_settings(max_generated_queries=4),
        )
        assert len(queries) > 1
        assert "What is the headquarters?" in queries

    def test_merge_multi_query_results_prefers_consensus(self) -> None:
        merged = merge_multi_query_results(
            [
                [_result("a", score=0.4), _result("b", score=0.9)],
                [_result("a", score=0.8), _result("c", score=0.7)],
            ],
            limit=2,
        )
        # Original-query reservation keeps both original hits before RRF fill.
        assert [item.chunk_id for item in merged] == ["a", "b"]

    def test_merge_reserves_original_query_hits(self) -> None:
        """Strong original-query evidence must not be drowned by expansion TOC hits."""
        original = [
            _result("toc", score=0.95),
            _result("body", score=0.90),
        ]
        # Many expansions only retrieve toc/noise — previously body fell out of top-N.
        expansions = [[_result("toc", score=0.9), _result(f"noise-{i}", score=0.8)] for i in range(6)]
        merged = merge_multi_query_results([original, *expansions], limit=4)
        assert "body" in {item.chunk_id for item in merged}


class TestStrategy:
    def test_financial_strategy_increases_sparse_weight(self) -> None:
        rules = get_rules()
        classification = classify_query("What is the quarterly revenue?")
        strategy = select_strategy(
            classification,
            registry=rules,
            hybrid_settings=HybridRetrievalSettings(sparse_weight=1.0, dense_weight=1.0),
            metadata_settings=MetadataRetrievalSettings(),
            reranking_settings=RerankingSettings(),
            settings=_settings(),
        )
        assert strategy.sparse_weight > 1.0
        assert strategy.dense_weight < 1.0

    def test_entity_lookup_strategy_reduces_rerank_top_n(self) -> None:
        rules = get_rules()
        classification = classify_query("Who is the CEO?")
        strategy = select_strategy(
            classification,
            registry=rules,
            hybrid_settings=HybridRetrievalSettings(),
            metadata_settings=MetadataRetrievalSettings(),
            reranking_settings=RerankingSettings(rerank_top_n=20),
            settings=_settings(),
        )
        assert strategy.rerank_top_n == 12

    def test_apply_strategy_changes_hybrid_depth(self) -> None:
        base = HybridRetrievalSettings(top_k_dense=20, top_k_sparse=20)
        strategy = select_strategy(
            classify_query("What related document is referenced?"),
            registry=get_rules(),
            hybrid_settings=base,
            metadata_settings=MetadataRetrievalSettings(),
            reranking_settings=RerankingSettings(),
            settings=_settings(),
        )
        effective = apply_strategy_to_hybrid_settings(base, strategy)
        assert effective.top_k_dense > base.top_k_dense


class TestProcessor:
    def test_process_expands_hq_query(self) -> None:
        processor = QueryProcessor(settings=_settings())
        outcome = processor.process("What is HQ?")
        assert outcome.original_query == "What is HQ?"
        assert "headquarters" in outcome.expanded_query.lower()
        assert outcome.retrieval_queries
        assert outcome.strategy.name

    def test_disabled_returns_passthrough(self) -> None:
        processor = QueryProcessor(settings=_settings(enabled=False))
        outcome = processor.process("What is HQ?")
        assert outcome.retrieval_queries == ("What is HQ?",)
        assert outcome.expanded_query == "What is HQ?"

    def test_fallback_on_registry_failure(self, monkeypatch) -> None:
        processor = QueryProcessor(settings=_settings())

        def _boom(_query: str):
            raise RuntimeError("classification failed")

        monkeypatch.setattr(
            "app.rag.query_processing.processor.classify_query",
            _boom,
        )
        outcome = processor.process("Who is the CEO?")
        assert outcome.fallback_used is True
        assert outcome.retrieval_queries == ("Who is the CEO?",)

    def test_deterministic_output(self) -> None:
        processor = QueryProcessor(settings=_settings())
        first = processor.process("What is the CEO headquarters location?")
        second = processor.process("What is the CEO headquarters location?")
        assert first.retrieval_queries == second.retrieval_queries
        assert first.strategy == second.strategy


class TestEngineIntegration:
    def test_search_invokes_query_processor(self, monkeypatch) -> None:
        from app.rag.engine import EnterpriseRAG

        faiss_store = MagicMock()
        faiss_store.size = 10
        hit = RetrievalResult(
            content="Singapore headquarters",
            source="doc.pdf",
            category="general",
            confidence=0.9,
            chunk_id="chunk-1",
        )

        hybrid_retriever = MagicMock()
        hybrid_retriever.search.return_value = [hit]

        query_processor = MagicMock()
        query_processor.process.return_value = MagicMock(
            original_query="What is HQ?",
            expanded_query="What is HQ? headquarters",
            retrieval_queries=("What is HQ?", "Where is the company headquarters?"),
            strategy=MagicMock(
                name="entity_lookup",
                sparse_weight=1.25,
                dense_weight=0.9,
                metadata_bonus_multiplier=1.0,
                rerank_top_n=12,
                retrieval_depth_multiplier=0.85,
            ),
            classification=MagicMock(category=MagicMock(value="entity_lookup")),
            detected_entities=("HQ",),
        )

        reranker = MagicMock()
        reranker.runtime = MagicMock()
        reranker.rerank.return_value = [hit]

        monkeypatch.setattr("app.rag.engine.HybridRetriever", lambda **kwargs: hybrid_retriever)
        monkeypatch.setattr(
            "app.rag.engine.MetadataAwareRetriever",
            lambda **kwargs: MagicMock(),
        )
        monkeypatch.setattr(
            "app.rag.engine.CrossEncoderReranker",
            lambda **kwargs: reranker,
        )

        engine = EnterpriseRAG(
            vector_store=faiss_store,
            hybrid_retriever=hybrid_retriever,
            reranker=reranker,
            query_processor=query_processor,
        )
        engine._standalone_bm25 = MagicMock()

        results = engine._search(
            "What is HQ?",
            top_k=5,
            allowed_categories={"general"},
            authorized_sources=None,
        )

        assert query_processor.process.called
        assert hybrid_retriever.search.call_count == 2
        assert reranker.rerank.called
        assert results
