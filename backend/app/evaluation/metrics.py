"""Retrieval and benchmark metric calculations."""

from __future__ import annotations

import re
from statistics import mean

from app.evaluation.schemas import (
    AggregateMetrics,
    CitationEvaluationResult,
    DatasetBreakdown,
    EvaluationCase,
    EvaluationDataset,
    ExpectedCitation,
    FailureSummary,
    FailureTypeSummary,
    QuestionResult,
    RetrievalEvaluationResult,
    RetrievedChunkDetail,
)
from app.evaluation.semantic_matcher import (
    evaluate_semantic_match,
    is_semantically_relevant,
)
from app.rag.types import Citation, RetrievalResult


def parse_chunk_index(chunk_id: str) -> int | None:
    """Extract the document-relative chunk index from a chunk id."""
    if "::" not in chunk_id:
        return None
    suffix = chunk_id.rsplit("::", maxsplit=1)[-1]
    try:
        return int(suffix)
    except ValueError:
        return None


def build_retrieved_chunk_details(
    results: list[RetrievalResult],
    *,
    case: EvaluationCase | None = None,
    preview_length: int = 160,
) -> list[RetrievedChunkDetail]:
    """Convert retrieval results into evaluation detail records."""
    details: list[RetrievedChunkDetail] = []
    for rank, result in enumerate(results, start=1):
        preview = result.content[:preview_length].strip()
        if len(result.content) > preview_length:
            preview += "..."
        chunk_index = parse_chunk_index(result.chunk_id)
        semantic_match = False
        match_reasons: list[str] = []
        legacy_chunk_match = False
        if case is not None:
            semantic_result = evaluate_semantic_match(result, case)
            semantic_match = semantic_result.is_relevant
            match_reasons = list(semantic_result.reasons)
            if chunk_index is not None and chunk_index in case.expected_chunks:
                legacy_chunk_match = True
        details.append(
            RetrievedChunkDetail(
                rank=rank,
                chunk_id=result.chunk_id,
                chunk_index=chunk_index,
                source=result.source,
                page_number=result.page_number,
                category=result.category,
                confidence=result.confidence,
                content_preview=preview,
                semantic_match=semantic_match,
                match_reasons=match_reasons,
                legacy_chunk_match=legacy_chunk_match,
            )
        )
    return details


def _first_semantic_rank(
    results: list[RetrievalResult],
    case: EvaluationCase,
) -> int | None:
    for rank, result in enumerate(results, start=1):
        if is_semantically_relevant(result, case):
            return rank
    return None


def _first_legacy_chunk_rank(
    retrieved_chunks: list[int],
    expected_chunks: list[int],
) -> int | None:
    for rank, chunk_index in enumerate(retrieved_chunks, start=1):
        if chunk_index in expected_chunks:
            return rank
    return None


def _semantic_recall_at_k(
    results: list[RetrievalResult],
    case: EvaluationCase,
    k: int,
) -> bool:
    for result in results[:k]:
        if is_semantically_relevant(result, case):
            return True
    return False


def _legacy_recall_at_k(retrieved_chunks: list[int], expected_chunks: list[int], k: int) -> bool:
    if not expected_chunks:
        return True
    top_k = set(retrieved_chunks[:k])
    return any(chunk in top_k for chunk in expected_chunks)


def _semantic_precision_at_k(
    results: list[RetrievalResult],
    case: EvaluationCase,
    k: int,
) -> float:
    if k <= 0:
        return 0.0
    top_k = results[:k]
    if not top_k:
        return 0.0
    relevant = sum(1 for result in top_k if is_semantically_relevant(result, case))
    return relevant / len(top_k)


def _legacy_precision_at_k(retrieved_chunks: list[int], expected_chunks: list[int], k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = retrieved_chunks[:k]
    if not top_k:
        return 0.0
    if not expected_chunks:
        return 1.0
    expected_set = set(expected_chunks)
    relevant = sum(1 for chunk in top_k if chunk in expected_set)
    return relevant / len(top_k)


def evaluate_retrieval(
    case: EvaluationCase,
    results: list[RetrievalResult],
    *,
    retrieval_top_k: int,
) -> RetrievalEvaluationResult:
    """Evaluate retrieval quality for a single benchmark case."""
    details = build_retrieved_chunk_details(results, case=case)
    retrieved_chunks = [
        index
        for index in (detail.chunk_index for detail in details)
        if index is not None
    ]

    expected_rank = _first_semantic_rank(results, case)
    semantic_match_found = expected_rank is not None
    legacy_chunk_match_found = (
        _first_legacy_chunk_rank(retrieved_chunks, case.expected_chunks) is not None
        if case.expected_chunks
        else False
    )

    if semantic_match_found:
        failure_reason = None if expected_rank == 1 else "expected_semantic_region_not_rank_1"
    else:
        failure_reason = "expected_semantic_region_not_in_top_k"

    mrr_contribution = 1.0 / expected_rank if expected_rank else 0.0

    return RetrievalEvaluationResult(
        retrieved_documents=[detail.source for detail in details],
        retrieved_chunks=retrieved_chunks,
        retrieved_pages=[detail.page_number for detail in details],
        similarity_scores=[detail.confidence for detail in details],
        expected_chunk_found=semantic_match_found,
        expected_rank=expected_rank,
        mrr_contribution=mrr_contribution,
        recall_at_1=_semantic_recall_at_k(results, case, 1),
        recall_at_3=_semantic_recall_at_k(results, case, 3),
        recall_at_5=_semantic_recall_at_k(results, case, 5),
        precision_at_k=_semantic_precision_at_k(results, case, retrieval_top_k),
        top_k_details=details,
        failure_reason=failure_reason,
        semantic_match_found=semantic_match_found,
        evaluation_method="semantic",
        legacy_chunk_match_found=legacy_chunk_match_found,
    )


_STOPWORDS = frozenset({
    "that", "this", "with", "from", "have", "been", "will", "your", "their",
    "about", "which", "when", "where", "what", "than", "then", "into", "also",
    "must", "shall", "should", "would", "could", "company", "document",
    "globaltrust", "financial", "services", "internal", "classification",
})


def _chunk_is_relevant(result: RetrievalResult, case: EvaluationCase) -> bool:
    return is_semantically_relevant(result, case)


def compute_context_precision(
    case: EvaluationCase,
    results: list[RetrievalResult],
) -> float:
    """Fraction of retrieved chunks that are relevant to the expected answer."""
    if not results:
        return 0.0
    relevant = sum(1 for result in results if _chunk_is_relevant(result, case))
    return relevant / len(results)


def _tokenize_for_grounding(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]{4,}", text.casefold())
    return {token for token in tokens if token not in _STOPWORDS}


def detect_hallucination(
    actual_answer: str,
    retrieval_results: list[RetrievalResult],
    *,
    expected_answer: str,
) -> bool:
    """Heuristic hallucination check: answer tokens not grounded in retrieved context."""
    if not actual_answer.strip():
        return False

    context_tokens: set[str] = set()
    for result in retrieval_results:
        context_tokens |= _tokenize_for_grounding(result.content)
    context_tokens |= _tokenize_for_grounding(expected_answer)

    answer_tokens = _tokenize_for_grounding(actual_answer)
    if not answer_tokens:
        return False

    unsupported = [token for token in answer_tokens if token not in context_tokens]
    unsupported_ratio = len(unsupported) / len(answer_tokens)
    return unsupported_ratio > 0.45 and len(unsupported) >= 2


def evaluate_citations(
    case: EvaluationCase,
    citations: list[Citation],
) -> CitationEvaluationResult:
    """Evaluate whether returned citations match expected sources and pages."""
    expected = case.expected_citations
    if not expected:
        expected = [
            ExpectedCitation(source=case.expected_document, page=case.expected_page)
        ]

    actual = [
        {
            "source": citation.source,
            "page": citation.page,
            "confidence": citation.confidence,
        }
        for citation in citations
    ]

    passed = True
    details: list[str] = []

    for expected_citation in expected:
        matching = [
            citation
            for citation in citations
            if citation.source == expected_citation.source
        ]
        if not matching:
            passed = False
            details.append(f"Missing citation for source '{expected_citation.source}'.")
            continue

        if expected_citation.page is not None:
            pages = {citation.page for citation in matching if citation.page is not None}
            if expected_citation.page not in pages:
                passed = False
                details.append(
                    f"Expected page {expected_citation.page} for "
                    f"'{expected_citation.source}', got {sorted(pages)}."
                )

    detail = "Citation expectations satisfied." if passed else " ".join(details)
    return CitationEvaluationResult(
        passed=passed,
        expected_citations=expected,
        actual_citations=actual,
        detail=detail,
    )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def aggregate_metrics(
    question_results: list[QuestionResult],
    *,
    retrieval_top_k: int,
) -> AggregateMetrics:
    """Compute aggregate metrics across all evaluated questions."""
    count = len(question_results)
    if count == 0:
        return AggregateMetrics(
            case_count=0,
            recall_at_1=0.0,
            recall_at_3=0.0,
            recall_at_5=0.0,
            mrr=0.0,
            precision_at_k=0.0,
            citation_accuracy=0.0,
            answer_accuracy=0.0,
            top_1_correct_pct=0.0,
            top_3_correct_pct=0.0,
            avg_retrieval_confidence=0.0,
            avg_retrieval_latency_ms=0.0,
            avg_generation_latency_ms=0.0,
            avg_total_latency_ms=0.0,
            p50_total_latency_ms=0.0,
            p95_total_latency_ms=0.0,
            context_precision=0.0,
            hallucination_rate=0.0,
        )

    total_latencies = [result.total_latency_ms for result in question_results]

    return AggregateMetrics(
        case_count=count,
        recall_at_1=mean(
            1.0 if result.retrieval.recall_at_1 else 0.0
            for result in question_results
        ),
        recall_at_3=mean(
            1.0 if result.retrieval.recall_at_3 else 0.0
            for result in question_results
        ),
        recall_at_5=mean(
            1.0 if result.retrieval.recall_at_5 else 0.0
            for result in question_results
        ),
        mrr=mean(result.retrieval.mrr_contribution for result in question_results),
        precision_at_k=mean(
            result.retrieval.precision_at_k for result in question_results
        ),
        citation_accuracy=mean(
            1.0 if result.citation.passed else 0.0
            for result in question_results
        ),
        answer_accuracy=mean(
            1.0 if result.answer.passed else 0.0 for result in question_results
        ),
        top_1_correct_pct=mean(
            1.0 if result.retrieval.expected_rank == 1 else 0.0
            for result in question_results
        ),
        top_3_correct_pct=mean(
            1.0
            if result.retrieval.expected_rank is not None
            and result.retrieval.expected_rank <= 3
            else 0.0
            for result in question_results
        ),
        avg_retrieval_confidence=mean(
            result.retrieval_confidence for result in question_results
        ),
        avg_retrieval_latency_ms=mean(
            result.retrieval_latency_ms for result in question_results
        ),
        avg_generation_latency_ms=mean(
            result.generation_latency_ms for result in question_results
        ),
        avg_total_latency_ms=mean(total_latencies),
        p50_total_latency_ms=_percentile(total_latencies, 0.50),
        p95_total_latency_ms=_percentile(total_latencies, 0.95),
        context_precision=mean(result.context_precision for result in question_results),
        hallucination_rate=mean(
            1.0 if result.hallucination_detected else 0.0
            for result in question_results
        ),
    )


def build_dataset_breakdown(dataset: EvaluationDataset) -> DatasetBreakdown:
    """Summarize case distribution across dataset dimensions."""
    by_document_type: dict[str, int] = {}
    by_difficulty: dict[str, int] = {}
    by_query_category: dict[str, int] = {}

    for case in dataset.cases:
        by_document_type[case.document_type] = by_document_type.get(case.document_type, 0) + 1
        by_difficulty[case.difficulty.value] = by_difficulty.get(case.difficulty.value, 0) + 1
        by_query_category[case.query_category.value] = (
            by_query_category.get(case.query_category.value, 0) + 1
        )

    return DatasetBreakdown(
        by_document_type=by_document_type,
        by_difficulty=by_difficulty,
        by_query_category=by_query_category,
    )


def build_failure_type_analysis(
    question_results: list[QuestionResult],
) -> list[FailureTypeSummary]:
    """Aggregate typed failure classifications."""
    buckets: dict[str, list[str]] = {}
    for result in question_results:
        for failure in result.failure_types:
            buckets.setdefault(failure.value, []).append(result.case_id)

    return [
        FailureTypeSummary(
            failure_type=failure_type,
            count=len(case_ids),
            case_ids=sorted(case_ids),
        )
        for failure_type, case_ids in sorted(
            buckets.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    ]


def build_failure_analysis(
    question_results: list[QuestionResult],
) -> list[FailureSummary]:
    """Aggregate failure reasons across benchmark cases."""
    buckets: dict[str, list[str]] = {}

    for result in question_results:
        reasons: list[str] = []
        if not result.retrieval.semantic_match_found:
            reasons.append("expected_semantic_region_not_in_top_k")
        elif result.retrieval.expected_rank != 1:
            reasons.append("expected_semantic_region_not_rank_1")
        if not result.answer.passed:
            reasons.append("answer_mismatch")
        if not result.citation.passed:
            reasons.append("citation_mismatch")
        if not result.access_granted:
            reasons.append("access_denied")

        if not reasons:
            continue

        for reason in reasons:
            buckets.setdefault(reason, []).append(result.case_id)

    return [
        FailureSummary(
            failure_reason=reason,
            count=len(case_ids),
            case_ids=sorted(case_ids),
        )
        for reason, case_ids in sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0]))
    ]


def identify_worst_performing(
    question_results: list[QuestionResult],
    *,
    limit: int = 5,
) -> list[str]:
    """Return case ids with the lowest combined retrieval and answer quality."""

    def _score(result: QuestionResult) -> float:
        retrieval_score = result.retrieval.mrr_contribution
        answer_score = 1.0 if result.answer.passed else 0.0
        citation_score = 1.0 if result.citation.passed else 0.0
        return retrieval_score + answer_score + citation_score

    ranked = sorted(question_results, key=_score)
    return [result.case_id for result in ranked[:limit]]
