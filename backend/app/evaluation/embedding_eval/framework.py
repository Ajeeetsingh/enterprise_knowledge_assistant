"""Production-grade multi-model embedding evaluation framework."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.config import get_settings
from app.embeddings.registry import EmbeddingModelSpec, resolve_model_specs
from app.embeddings.runtime import create_embedding_runtime
from app.evaluation.bootstrap import bootstrap_evaluation_corpus
from app.evaluation.dataset.loader import load_dataset, resolve_default_dataset_path
from app.evaluation.embedding_eval.cache import save_cached_bootstrap_metadata
from app.evaluation.embedding_eval.comparison import (
    build_comparison_report,
    render_comparison_table,
)
from app.evaluation.embedding_eval.metrics import build_model_metrics, export_metrics_json
from app.evaluation.embedding_eval.schemas import (
    EmbeddingComparisonReport,
    EmbeddingEvaluationConfig,
    EmbeddingModelMetrics,
)
from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import BenchmarkRunConfig
from app.services.rag_service import _create_engine

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RESULTS_DIR = BACKEND_ROOT / "evaluation_results"


class EmbeddingEvaluationFramework:
    """Evaluate multiple embedding models against the golden benchmark."""

    def __init__(
        self,
        *,
        runner: EvaluationRunner | None = None,
    ) -> None:
        self._runner = runner or EvaluationRunner()

    def evaluate_model(
        self,
        spec: EmbeddingModelSpec,
        config: EmbeddingEvaluationConfig,
        *,
        dataset_path: Path,
        dataset,
    ) -> EmbeddingModelMetrics:
        """Rebuild embeddings/index for one model and run the full benchmark."""
        runtime = create_embedding_runtime(spec)
        storage_path = (
            Path(config.results_dir or DEFAULT_RESULTS_DIR)
            / "embedding_storage"
            / spec.id
        )
        bootstrap = bootstrap_evaluation_corpus(
            corpus_path=config.corpus_path,
            include_documents=config.include_documents,
            embedding_runtime=runtime,
            storage_path=storage_path,
        )

        settings = get_settings()
        if config.llm_provider_override:
            settings = settings.model_copy(
                update={"llm_provider": config.llm_provider_override}
            )

        engine, _ = _create_engine(bootstrap.vector_store, settings)
        from app.evaluation.runner import PipelineContext

        context = PipelineContext(
            settings=settings,
            vector_store=bootstrap.vector_store,
            engine=engine,
            bootstrap=bootstrap,
            prompt_builder=self._runner._prompt_builder,
        )

        benchmark_config = BenchmarkRunConfig(
            corpus_path=config.corpus_path,
            results_dir=config.results_dir,
            role=config.role,
            retrieval_top_k=config.retrieval_top_k,
            llm_provider_override=config.llm_provider_override,
            include_documents=config.include_documents,
            embedding_model_id=spec.id,
            run_label=config.run_label or f"embedding_eval_{spec.id}",
            compare_previous=False,
            compare_best=False,
            capture_artifacts=False,
            generate_dashboard=False,
        )

        report = self._runner.run_dataset(
            dataset,
            benchmark_config,
            dataset_path=str(dataset_path),
            run_id=str(uuid4()),
            context=context,
        )

        if config.use_cache:
            save_cached_bootstrap_metadata(
                bootstrap=bootstrap,
                corpus_path=bootstrap.corpus_path,
                include_documents=config.include_documents,
            )

        return build_model_metrics(
            spec=spec,
            bootstrap=bootstrap,
            report=report,
        )

    def run(self, config: EmbeddingEvaluationConfig | None = None) -> EmbeddingComparisonReport:
        """Evaluate all configured models and produce a comparison report."""
        resolved = config or EmbeddingEvaluationConfig()
        started_at = datetime.now(UTC)

        dataset_path = (
            Path(resolved.dataset_path)
            if resolved.dataset_path
            else resolve_default_dataset_path()
        )
        dataset = load_dataset(dataset_path)
        specs = resolve_model_specs(
            resolved.model_ids,
            registry_path=resolved.registry_path,
        )

        results_dir = (
            Path(resolved.results_dir)
            if resolved.results_dir
            else DEFAULT_RESULTS_DIR
        )
        results_dir.mkdir(parents=True, exist_ok=True)

        model_metrics: list[EmbeddingModelMetrics] = []
        for spec in specs:
            logger.info("Evaluating embedding model: %s", spec.id)
            model_metrics.append(
                self.evaluate_model(
                    spec,
                    resolved,
                    dataset_path=dataset_path,
                    dataset=dataset,
                )
            )

        corpus_path = str(
            Path(resolved.corpus_path)
            if resolved.corpus_path
            else BACKEND_ROOT.parent / "data"
        )
        completed_at = datetime.now(UTC)
        comparison = build_comparison_report(
            started_at=started_at,
            completed_at=completed_at,
            dataset_path=str(dataset_path),
            corpus_path=corpus_path,
            case_count=len(dataset.cases),
            model_metrics=model_metrics,
            metadata={
                "evaluation_framework": "embedding_eval_v1",
                "models_evaluated": [spec.id for spec in specs],
            },
        )

        label = resolved.run_label or "embedding_comparison"
        comparison_path = results_dir / f"{label}.json"
        comparison_path.write_text(
            json.dumps(comparison.to_dict(), indent=2),
            encoding="utf-8",
        )
        table_path = results_dir / f"{label}_table.md"
        table_path.write_text(render_comparison_table(comparison.model_metrics), encoding="utf-8")
        export_metrics_json(model_metrics, results_dir / f"{label}_metrics.json")

        return comparison
