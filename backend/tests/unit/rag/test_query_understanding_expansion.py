"""Regression tests for Query Understanding & enterprise expansion (Phase 2A)."""

from __future__ import annotations

import pytest

from app.rag.query_processing.config import QueryProcessingSettings
from app.rag.query_processing.enterprise_expansion import expand_from_understanding
from app.rag.query_processing.processor import QueryProcessor
from app.rag.query_processing.understanding import understand_query


def _processor(max_queries: int = 8) -> QueryProcessor:
    return QueryProcessor(
        settings=QueryProcessingSettings(
            enabled=True,
            query_expansion_enabled=True,
            multi_query_enabled=True,
            max_generated_queries=max_queries,
            entity_normalization_enabled=True,
            synonym_expansion_enabled=True,
            strategy_selection_enabled=True,
        )
    )


ACCEPTANCE_CASES: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [
    (
        "What is Apex National Bank's mission, vision, and core values?",
        ("mission", "vision", "core_values"),
        ("mission", "vision", "core values", "company values"),
    ),
    (
        "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
        ("metadata",),
        ("metadata", "metadata categories", "enterprise metadata"),
    ),
    (
        "Explain the hierarchy used in the Enterprise Knowledge Taxonomy.",
        ("taxonomy",),
        ("taxonomy", "knowledge taxonomy", "taxonomy hierarchy"),
    ),
    (
        "What is the approval matrix for expenses?",
        ("approval",),
        ("approval matrix", "approval authority", "approval"),
    ),
    (
        "What is the leave encashment policy?",
        ("leave",),
        ("leave encashment", "leave policy", "leave payout"),
    ),
    (
        "What is the records retention schedule?",
        ("retention",),
        ("records retention", "retention schedule", "retention"),
    ),
    (
        "Describe the committee governance structure.",
        ("committee",),
        ("committee governance", "committee charter", "governance"),
    ),
    (
        "Explain the business process classification guide.",
        ("business_process",),
        ("business process", "process classification"),
    ),
]


@pytest.mark.parametrize("question,concepts,must_include", ACCEPTANCE_CASES)
def test_understanding_detects_concepts(
    question: str,
    concepts: tuple[str, ...],
    must_include: tuple[str, ...],
) -> None:
    understanding = understand_query(question)
    for concept in concepts:
        assert concept in understanding.concepts, (
            f"{question!r} missing concept {concept}; got {understanding.concepts}"
        )
    assert understanding.intent
    assert understanding.confidence > 0.4
    _ = must_include  # used in expansion test


@pytest.mark.parametrize("question,concepts,must_include", ACCEPTANCE_CASES)
def test_expansion_generates_meaningful_retrieval_queries(
    question: str,
    concepts: tuple[str, ...],
    must_include: tuple[str, ...],
) -> None:
    understanding = understand_query(question)
    queries, rules, strategy = expand_from_understanding(
        original_query=question,
        understanding=understanding,
        max_queries=8,
    )
    assert queries[0] == question
    assert len(queries) >= 4, f"{question!r} only produced {queries}"
    joined = " | ".join(q.lower() for q in queries)
    for fragment in must_include:
        assert fragment.lower() in joined, (
            f"{question!r} expansions missing {fragment!r}: {queries}"
        )
    assert "enterprise_understanding" in rules
    assert strategy
    assert concepts  # sanity


@pytest.mark.parametrize("question,concepts,must_include", ACCEPTANCE_CASES)
def test_processor_preserves_original_and_expands(
    question: str,
    concepts: tuple[str, ...],
    must_include: tuple[str, ...],
) -> None:
    outcome = _processor().process(question)
    assert outcome.original_query == question
    assert outcome.retrieval_queries[0] == question
    assert outcome.metrics is not None
    assert outcome.metrics.generated_query_count >= 4
    assert outcome.expansion_strategy
    assert outcome.understanding_intent
    assert set(concepts) & set(outcome.understanding_concepts)
    joined = " | ".join(q.lower() for q in outcome.retrieval_queries)
    for fragment in must_include[:2]:
        assert fragment.lower() in joined


def test_ethical_principles_maps_to_core_values() -> None:
    understanding = understand_query("What are the company's ethical principles?")
    assert "core_values" in understanding.concepts
    queries, _, _ = expand_from_understanding(
        original_query="What are the company's ethical principles?",
        understanding=understanding,
        max_queries=8,
    )
    joined = " ".join(queries).lower()
    assert "ethical principles" in joined or "core values" in joined


def test_over_expansion_is_capped() -> None:
    question = "What is Apex National Bank's mission, vision, and core values?"
    understanding = understand_query(question)
    queries, _, _ = expand_from_understanding(
        original_query=question,
        understanding=understanding,
        max_queries=6,
    )
    assert len(queries) <= 6
    assert queries[0] == question
