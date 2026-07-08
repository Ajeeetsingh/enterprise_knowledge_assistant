"""Unit tests for the embedding evaluation framework orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.evaluation.embedding_eval.framework import EmbeddingEvaluationFramework
from app.evaluation.embedding_eval.schemas import EmbeddingEvaluationConfig
from app.evaluation.schemas import AggregateMetrics, AnswerMatchMode, BenchmarkReport
from app.embeddings.registry import get_model_spec


def _benchmark_report() -> BenchmarkReport:
    return BenchmarkReport(
        run_id="run-1",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        dataset_version="2.0.0",
        dataset_path="dataset.json",
        corpus_path="data",
        role="admin",
        retrieval_top_k=5,
        answer_match_mode=AnswerMatchMode.CONTAINS,
        metrics=AggregateMetrics(
            case_count=2,
            recall_at_1=0.5,
            recall_at_3=0.5,
            recall_at_5=1.0,
            mrr=0.75,
            precision_at_k=0.5,
            citation_accuracy=0.5,
            answer_accuracy=0.5,
            top_1_correct_pct=0.5,
            top_3_correct_pct=0.5,
            avg_retrieval_confidence=0.4,
            avg_retrieval_latency_ms=12.0,
            avg_generation_latency_ms=1.0,
            avg_total_latency_ms=13.0,
            p50_total_latency_ms=13.0,
            p95_total_latency_ms=13.0,
            context_precision=0.5,
            hallucination_rate=0.0,
        ),
        question_results=[],
        failure_analysis=[],
        failure_type_analysis=[],
        dataset_breakdown=None,
        worst_performing=[],
    )


def test_framework_evaluates_models_without_touching_production_singleton(
    tmp_path: Path,
) -> None:
    spec = get_model_spec("minilm-l6-v2")
    bootstrap = MagicMock()
    bootstrap.vector_store = MagicMock()
    bootstrap.corpus_path = tmp_path / "data"
    bootstrap.embedding_model_id = spec.id
    bootstrap.embedding_model_name = spec.model_name
    bootstrap.embedding_dimension = 384
    bootstrap.model_load_ms = 10.0
    bootstrap.embedding_time_ms = 100.0
    bootstrap.index_build_ms = 120.0
    bootstrap.index_size_bytes = 1024
    bootstrap.total_chunks = 50
    bootstrap.indexed_documents = ["doc.pdf"]

    runner = MagicMock()
    runner._prompt_builder = MagicMock()
    runner.run_dataset.return_value = _benchmark_report()

    framework = EmbeddingEvaluationFramework(runner=runner)
    config = EmbeddingEvaluationConfig(
        results_dir=str(tmp_path / "results"),
        model_ids=["minilm-l6-v2"],
        use_cache=False,
    )

    with patch(
        "app.evaluation.embedding_eval.framework.bootstrap_evaluation_corpus",
        return_value=bootstrap,
    ) as bootstrap_mock, patch(
        "app.evaluation.embedding_eval.framework.create_embedding_runtime"
    ) as runtime_mock, patch(
        "app.evaluation.embedding_eval.framework._create_engine",
        return_value=(MagicMock(), 50),
    ), patch(
        "app.evaluation.embedding_eval.framework.load_dataset"
    ) as load_dataset_mock:
        dataset = MagicMock()
        dataset.cases = [MagicMock(), MagicMock()]
        dataset.version = "2.0.0"
        load_dataset_mock.return_value = dataset

        report = framework.run(config)

    runtime_mock.assert_called_once()
    bootstrap_mock.assert_called_once()
    runner.run_dataset.assert_called_once()
    assert report.recommended_model_id == "minilm-l6-v2"
    assert (tmp_path / "results" / "embedding_comparison.json").exists()
