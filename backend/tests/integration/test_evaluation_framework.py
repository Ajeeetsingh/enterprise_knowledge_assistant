"""Integration tests for the retrieval evaluation framework."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.benchmark import run_benchmark
from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import AnswerMatchMode, BenchmarkRunConfig


SAMPLE_TEXT = (
    "GlobalTrust Financial Services is headquartered in Singapore. "
    "Sarah Mitchell serves as Chief Executive Officer. "
    "The company was founded in 1987. "
    "GlobalTrust operates in over 20 countries."
)


@pytest.fixture
def evaluation_dataset_path(tmp_path: Path) -> Path:
    payload = {
        "version": "integration-1",
        "description": "Integration benchmark dataset",
        "cases": [
            {
                "id": "INT-001",
                "question": "What is the company headquarters?",
                "expected_answer": "Singapore",
                "expected_document": "GTFS-EXEC-001_Company_Overview.txt",
                "expected_chunks": [0],
                "category": "general",
                "difficulty": "easy",
                "document_type": "overview",
                "query_category": "factual_lookup",
                "tags": ["hq"],
                "answer_match_mode": "contains",
                "role": "admin",
                "authorized_sources": ["GTFS-EXEC-001_Company_Overview.txt"],
            },
            {
                "id": "INT-002",
                "question": "Who is the Chief Executive Officer?",
                "expected_answer": "Sarah Mitchell",
                "expected_document": "GTFS-EXEC-001_Company_Overview.txt",
                "expected_chunks": [0],
                "category": "general",
                "difficulty": "easy",
                "document_type": "overview",
                "query_category": "factual_lookup",
                "tags": ["ceo"],
                "answer_match_mode": "contains",
                "role": "admin",
                "authorized_sources": ["GTFS-EXEC-001_Company_Overview.txt"],
            },
        ],
    }
    dataset_path = tmp_path / "integration_dataset.json"
    dataset_path.write_text(json.dumps(payload), encoding="utf-8")
    return dataset_path


@pytest.fixture
def evaluation_corpus_path(tmp_path: Path) -> Path:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    document_path = corpus_dir / "GTFS-EXEC-001_Company_Overview.txt"
    document_path.write_text(SAMPLE_TEXT, encoding="utf-8")
    return corpus_dir


@pytest.mark.integration
def test_evaluation_runner_executes_real_pipeline(
    evaluation_dataset_path: Path,
    evaluation_corpus_path: Path,
    tmp_path: Path,
) -> None:
    pytest.importorskip("faiss")
    pytest.importorskip("sentence_transformers")

    from app.evaluation.dataset.loader import load_dataset

    dataset = load_dataset(evaluation_dataset_path)
    config = BenchmarkRunConfig(
        corpus_path=str(evaluation_corpus_path),
        results_dir=str(tmp_path / "results"),
        retrieval_top_k=3,
        answer_match_mode=AnswerMatchMode.CONTAINS,
        llm_provider_override="none",
    )

    runner = EvaluationRunner()
    report = runner.run_dataset(
        dataset,
        config,
        dataset_path=str(evaluation_dataset_path),
    )

    assert report.metrics.case_count == 2
    assert report.metrics.recall_at_1 >= 0.5
    assert report.metrics.answer_accuracy >= 0.5
    assert all(result.access_granted for result in report.question_results)
    assert all(
        result.generation_backend in {"answer_generator", "llm", "none"}
        for result in report.question_results
    )


@pytest.mark.integration
def test_run_benchmark_cli_exports_reports(
    evaluation_dataset_path: Path,
    evaluation_corpus_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("faiss")
    pytest.importorskip("sentence_transformers")

    results_dir = tmp_path / "results"
    argv = [
        "benchmark",
        "--dataset",
        str(evaluation_dataset_path),
        "--corpus",
        str(evaluation_corpus_path),
        "--results-dir",
        str(results_dir),
        "--top-k",
        "3",
        "--llm-provider",
        "none",
        "--no-compare",
        "--label",
        "integration",
    ]
    monkeypatch.setattr("sys.argv", argv)

    exit_code = run_benchmark()
    assert exit_code == 0
    assert any(results_dir.glob("run_*.json"))
    assert any(results_dir.glob("integration.json"))
    assert any(results_dir.glob("integration_questions.csv"))
    assert any(results_dir.glob("integration_summary.csv"))
