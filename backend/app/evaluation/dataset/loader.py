"""Load and validate golden evaluation datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.evaluation.schemas import (
    AnswerMatchMode,
    Difficulty,
    EvaluationCase,
    EvaluationDataset,
    ExpectedCitation,
    QueryCategory,
)

BACKEND_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parent / "golden_dataset.json"
)
FULL_DATASET_PATH = (
    Path(__file__).resolve().parent / "golden_dataset_full.json"
)


class DatasetValidationError(ValueError):
    """Raised when a golden dataset fails validation."""


def resolve_default_dataset_path() -> Path:
    """Return the path to the bundled golden dataset."""
    if FULL_DATASET_PATH.exists():
        return FULL_DATASET_PATH
    return DEFAULT_DATASET_PATH


def _parse_citation(raw: dict[str, Any]) -> ExpectedCitation:
    return ExpectedCitation(
        source=str(raw["source"]),
        page=raw.get("page"),
    )


def _parse_case(raw: dict[str, Any]) -> EvaluationCase:
    required = ("id", "question", "expected_answer", "expected_document")
    missing = [field for field in required if field not in raw]
    if missing:
        raise DatasetValidationError(
            f"Case is missing required fields: {', '.join(missing)}"
        )

    expected_citations = [
        _parse_citation(item) for item in raw.get("expected_citations", [])
    ]
    if not expected_citations and raw.get("expected_document"):
        expected_citations = [
            ExpectedCitation(
                source=str(raw["expected_document"]),
                page=raw.get("expected_page"),
            )
        ]

    difficulty_raw = str(raw.get("difficulty", Difficulty.MEDIUM.value)).lower()
    try:
        difficulty = Difficulty(difficulty_raw)
    except ValueError as exc:
        raise DatasetValidationError(
            f"Invalid difficulty '{difficulty_raw}' for case {raw['id']}"
        ) from exc

    mode_raw = str(raw.get("answer_match_mode", AnswerMatchMode.CONTAINS.value)).lower()
    try:
        answer_match_mode = AnswerMatchMode(mode_raw)
    except ValueError as exc:
        raise DatasetValidationError(
            f"Invalid answer_match_mode '{mode_raw}' for case {raw['id']}"
        ) from exc

    query_category_raw = str(
        raw.get("query_category", QueryCategory.FACTUAL_LOOKUP.value)
    ).lower()
    try:
        query_category = QueryCategory(query_category_raw)
    except ValueError as exc:
        raise DatasetValidationError(
            f"Invalid query_category '{query_category_raw}' for case {raw['id']}"
        ) from exc

    return EvaluationCase(
        id=str(raw["id"]),
        question=str(raw["question"]),
        expected_answer=str(raw["expected_answer"]),
        expected_document=str(raw["expected_document"]),
        expected_page=raw.get("expected_page"),
        expected_page_end=raw.get("expected_page_end"),
        expected_section_title=raw.get("expected_section_title"),
        expected_hierarchy_path=tuple(raw.get("expected_hierarchy_path", [])),
        expected_semantic_region=raw.get("expected_semantic_region"),
        expected_chunks=[int(value) for value in raw.get("expected_chunks", [])],
        category=str(raw.get("category", "general")),
        expected_citations=expected_citations,
        difficulty=difficulty,
        document_type=str(raw.get("document_type", "general")),
        query_category=query_category,
        tags=[str(tag) for tag in raw.get("tags", [])],
        answer_match_mode=answer_match_mode,
        role=str(raw.get("role", "admin")),
        authorized_sources=raw.get("authorized_sources"),
        notes=raw.get("notes"),
    )


def _validate_dataset(dataset: EvaluationDataset) -> None:
    if not dataset.cases:
        raise DatasetValidationError("Dataset must contain at least one case.")

    seen_ids: set[str] = set()
    for case in dataset.cases:
        if case.id in seen_ids:
            raise DatasetValidationError(f"Duplicate case id: {case.id}")
        seen_ids.add(case.id)
        if not case.question.strip():
            raise DatasetValidationError(f"Case {case.id} has an empty question.")
        if not case.expected_answer.strip():
            raise DatasetValidationError(f"Case {case.id} has an empty expected_answer.")


def load_dataset(path: str | Path | None = None) -> EvaluationDataset:
    """Load a golden evaluation dataset from JSON."""
    dataset_path = Path(path) if path is not None else resolve_default_dataset_path()
    if not dataset_path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {dataset_path}")

    with dataset_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise DatasetValidationError("Dataset root must be a JSON object.")

    cases_raw = payload.get("cases", [])
    if not isinstance(cases_raw, list):
        raise DatasetValidationError("'cases' must be a list.")

    dataset = EvaluationDataset(
        version=str(payload.get("version", "1.0")),
        description=str(payload.get("description", "")),
        cases=[_parse_case(item) for item in cases_raw],
        metadata=dict(payload.get("metadata", {})),
    )
    _validate_dataset(dataset)
    return dataset
