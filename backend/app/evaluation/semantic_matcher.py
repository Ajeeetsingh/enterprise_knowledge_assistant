"""Semantic retrieval matching for the evaluation framework."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.evaluation.schemas import EvaluationCase
from app.rag.types import RetrievalResult

_TOKEN_RE = re.compile(r"[a-z0-9]{4,}")
_PAGE_TOLERANCE = 1
_MIN_REGION_TOKEN_OVERLAP = 0.22
_MIN_SHARED_PHRASE_CHARS = 18


@dataclass(frozen=True)
class SemanticExpectation:
    """Resolved semantic retrieval target for a benchmark case."""

    document: str
    page_start: int | None
    page_end: int | None
    section_title: str | None
    hierarchy_path: tuple[str, ...]
    semantic_region: str
    answer_anchor: str


@dataclass(frozen=True)
class SemanticMatchResult:
    """Outcome of semantic relevance scoring for one retrieved chunk."""

    is_relevant: bool
    reasons: tuple[str, ...]
    document_match: bool
    page_match: bool
    content_match: bool
    section_match: bool


def resolve_semantic_expectation(case: EvaluationCase) -> SemanticExpectation:
    """Build semantic expectations from a case, with legacy field fallbacks."""
    page_end = case.expected_page_end if case.expected_page_end is not None else case.expected_page
    region = (
        case.expected_semantic_region
        or case.notes
        or case.expected_answer
        or ""
    )
    return SemanticExpectation(
        document=case.expected_document,
        page_start=case.expected_page,
        page_end=page_end,
        section_title=case.expected_section_title,
        hierarchy_path=case.expected_hierarchy_path,
        semantic_region=region.strip(),
        answer_anchor=case.expected_answer.strip(),
    )


def _significant_tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.casefold()) if token not in _STOPWORDS]


_STOPWORDS = frozenset({
    "that", "this", "with", "from", "have", "been", "will", "your", "their",
    "about", "which", "when", "where", "what", "than", "then", "into", "also",
    "must", "shall", "should", "would", "could", "company", "document",
    "globaltrust", "financial", "services", "internal", "classification",
    "confidential", "gtfs",
})


def _longest_shared_phrase(left: str, right: str) -> int:
    left_cf = left.casefold()
    right_cf = right.casefold()
    best = 0
    for size in range(min(len(left_cf), len(right_cf)), _MIN_SHARED_PHRASE_CHARS - 1, -1):
        for start in range(0, len(left_cf) - size + 1):
            fragment = left_cf[start : start + size]
            if fragment.strip() and fragment in right_cf:
                return size
    return best


def _content_region_match(content: str, expectation: SemanticExpectation) -> bool:
    content_cf = content.casefold()
    if expectation.answer_anchor and len(expectation.answer_anchor) >= 3:
        if expectation.answer_anchor.casefold() in content_cf:
            return True

    if not expectation.semantic_region:
        return False

    region_tokens = _significant_tokens(expectation.semantic_region)
    if region_tokens:
        content_token_set = set(_significant_tokens(content))
        overlap = sum(1 for token in region_tokens if token in content_token_set)
        if overlap / len(region_tokens) >= _MIN_REGION_TOKEN_OVERLAP:
            return True

    if _longest_shared_phrase(expectation.semantic_region, content) >= _MIN_SHARED_PHRASE_CHARS:
        return True

    return False


def _page_values(result: RetrievalResult) -> tuple[int | None, int | None]:
    page_start = result.page_start if result.page_start is not None else result.page_number
    page_end = result.page_end if result.page_end is not None else page_start
    return page_start, page_end


def _page_match(result: RetrievalResult, expectation: SemanticExpectation) -> bool:
    if expectation.page_start is None:
        return True

    page_start, page_end = _page_values(result)
    if page_start is None:
        return False

    expected_start = max(1, expectation.page_start - _PAGE_TOLERANCE)
    expected_end = (expectation.page_end or expectation.page_start) + _PAGE_TOLERANCE
    chunk_end = page_end or page_start
    return not (chunk_end < expected_start or page_start > expected_end)


def _section_match(result: RetrievalResult, expectation: SemanticExpectation) -> bool:
    if not expectation.section_title and not expectation.hierarchy_path:
        return True

    if expectation.section_title:
        candidate_titles = [
            result.section_title,
            " ".join(result.hierarchy_path or ()),
        ]
        target = expectation.section_title.casefold()
        if any(title and target in title.casefold() for title in candidate_titles):
            return True
        target_tokens = set(_significant_tokens(expectation.section_title))
        for title in candidate_titles:
            if title and target_tokens:
                title_tokens = set(_significant_tokens(title))
                if target_tokens & title_tokens:
                    return True

    if expectation.hierarchy_path:
        retrieved_path = result.hierarchy_path or ()
        if retrieved_path and expectation.hierarchy_path == retrieved_path[: len(expectation.hierarchy_path)]:
            return True
        if retrieved_path and expectation.hierarchy_path[-1].casefold() in retrieved_path[-1].casefold():
            return True

    return not expectation.section_title and not expectation.hierarchy_path


def evaluate_semantic_match(
    result: RetrievalResult,
    case: EvaluationCase,
) -> SemanticMatchResult:
    """Return whether a retrieved chunk semantically satisfies the case expectation."""
    expectation = resolve_semantic_expectation(case)
    document_match = result.source == expectation.document
    page_match = _page_match(result, expectation)
    content_match = _content_region_match(result.content, expectation)
    section_match = _section_match(result, expectation)

    reasons: list[str] = []
    if document_match:
        reasons.append("document_match")
    if page_match:
        reasons.append("page_match")
    if content_match:
        reasons.append("semantic_region_match")
    if section_match and (expectation.section_title or expectation.hierarchy_path):
        reasons.append("section_match")

    is_relevant = (
        document_match
        and content_match
        and page_match
        and section_match
    )

    return SemanticMatchResult(
        is_relevant=is_relevant,
        reasons=tuple(reasons),
        document_match=document_match,
        page_match=page_match,
        content_match=content_match,
        section_match=section_match,
    )


def is_semantically_relevant(result: RetrievalResult, case: EvaluationCase) -> bool:
    """Return True when the retrieved chunk matches semantic expectations."""
    return evaluate_semantic_match(result, case).is_relevant
