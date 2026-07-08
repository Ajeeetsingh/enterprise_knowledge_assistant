"""Typed failure classification for benchmark post-mortem analysis."""

from __future__ import annotations

import re

from app.evaluation.schemas import (
    EvaluationCase,
    FailureType,
    QuestionResult,
)

_TABLE_NOISE_PATTERNS = (
    r"Jurisdiction\s+Primary\s+Function",
    r"Country\s*/\s*Jurisdiction",
    r"Office\s+Country",
    r"\|\s*Classification\s*\|",
)

_CONFIDENCE_LOW_THRESHOLD = 0.35


def _answer_has_table_parsing_noise(answer: str) -> bool:
    return any(re.search(pattern, answer, re.IGNORECASE) for pattern in _TABLE_NOISE_PATTERNS)


def _retrieved_has_table_noise(results_content: list[str]) -> bool:
    merged = " ".join(results_content)
    return any(re.search(pattern, merged, re.IGNORECASE) for pattern in _TABLE_NOISE_PATTERNS)


def classify_failures(
    case: EvaluationCase,
    result: QuestionResult,
    *,
    retrieved_chunk_contents: list[str] | None = None,
    confidence_low_threshold: float = _CONFIDENCE_LOW_THRESHOLD,
) -> list[FailureType]:
    """Classify all failure modes for a single benchmark case."""
    failures: list[FailureType] = []

    if not result.access_granted:
        return [FailureType.RBAC_FILTERING]

    if not result.retrieval.retrieved_documents:
        failures.append(FailureType.RETRIEVAL_FAILURE)
    elif not result.retrieval.semantic_match_found:
        failures.append(FailureType.RETRIEVAL_FAILURE)
    elif result.retrieval.expected_rank is not None and result.retrieval.expected_rank > 1:
        failures.append(FailureType.RANKING_FAILURE)

    if result.access_granted and result.retrieval.retrieved_chunks and not result.answer.passed:
        failures.append(FailureType.GENERATION_FAILURE)

    if not result.citation.passed and result.access_granted:
        failures.append(FailureType.CITATION_FAILURE)

    if (
        result.access_granted
        and result.retrieval_confidence > 0
        and result.retrieval_confidence < confidence_low_threshold
        and not result.retrieval.recall_at_1
    ):
        failures.append(FailureType.CONFIDENCE_ISSUE)

    contents = retrieved_chunk_contents or [
        detail.content_preview for detail in result.retrieval.top_k_details
    ]
    if _retrieved_has_table_noise(contents) or _answer_has_table_parsing_noise(
        result.answer.actual_answer
    ):
        if FailureType.GENERATION_FAILURE in failures or FailureType.RANKING_FAILURE in failures:
            failures.append(FailureType.TABLE_PARSING)

    if result.hallucination_detected:
        failures.append(FailureType.HALLUCINATION)

    if result.context_precision < 0.5 and result.retrieval.retrieved_documents:
        failures.append(FailureType.CONTEXT_NOISE)

    # Deduplicate while preserving order
    seen: set[FailureType] = set()
    ordered: list[FailureType] = []
    for failure in failures:
        if failure not in seen:
            seen.add(failure)
            ordered.append(failure)
    return ordered


def aggregate_failure_types(
    question_results: list[QuestionResult],
) -> dict[str, list[str]]:
    """Group case ids by classified failure type."""
    buckets: dict[str, list[str]] = {}
    for result in question_results:
        for failure in result.failure_types:
            buckets.setdefault(failure.value, []).append(result.case_id)
    return {
        failure_type: sorted(case_ids)
        for failure_type, case_ids in sorted(buckets.items())
    }
