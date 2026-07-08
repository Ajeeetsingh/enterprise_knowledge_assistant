"""Unit tests for golden dataset loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.dataset.loader import (
    DatasetValidationError,
    load_dataset,
    resolve_default_dataset_path,
)
from app.evaluation.schemas import AnswerMatchMode, Difficulty


def test_resolve_default_dataset_path_exists() -> None:
    path = resolve_default_dataset_path()
    assert path.exists()
    assert path.name in {"golden_dataset.json", "golden_dataset_full.json"}


def test_load_default_dataset() -> None:
    dataset = load_dataset()
    assert dataset.version
    assert len(dataset.cases) >= 100
    first = dataset.cases[0]
    assert first.query_category is not None


def test_load_dataset_from_custom_file(tmp_path: Path) -> None:
    payload = {
        "version": "test-1",
        "description": "custom",
        "cases": [
            {
                "id": "CASE-1",
                "question": "What is X?",
                "expected_answer": "X",
                "expected_document": "doc.pdf",
                "expected_chunks": [0],
                "difficulty": "hard",
                "answer_match_mode": "exact",
            }
        ],
    }
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(payload), encoding="utf-8")

    dataset = load_dataset(dataset_path)
    assert dataset.version == "test-1"
    assert len(dataset.cases) == 1
    assert dataset.cases[0].difficulty is Difficulty.HARD
    assert dataset.cases[0].answer_match_mode is AnswerMatchMode.EXACT


def test_duplicate_case_ids_raise_validation_error(tmp_path: Path) -> None:
    payload = {
        "cases": [
            {
                "id": "DUP",
                "question": "Q1",
                "expected_answer": "A1",
                "expected_document": "doc.pdf",
            },
            {
                "id": "DUP",
                "question": "Q2",
                "expected_answer": "A2",
                "expected_document": "doc.pdf",
            },
        ]
    }
    dataset_path = tmp_path / "bad.json"
    dataset_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DatasetValidationError, match="Duplicate case id"):
        load_dataset(dataset_path)


def test_missing_required_field_raises_validation_error(tmp_path: Path) -> None:
    payload = {
        "cases": [
            {
                "id": "CASE-1",
                "question": "What?",
            }
        ]
    }
    dataset_path = tmp_path / "bad.json"
    dataset_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DatasetValidationError, match="missing required fields"):
        load_dataset(dataset_path)
