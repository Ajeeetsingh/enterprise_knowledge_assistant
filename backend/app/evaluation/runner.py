"""Benchmark runner that executes the real production RAG pipeline."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings, get_settings
from app.evaluation.answer_evaluator import AnswerEvaluator, get_answer_evaluator
from app.evaluation.artifacts import build_question_artifact, save_question_artifact
from app.evaluation.bootstrap import BootstrapResult, bootstrap_evaluation_corpus
from app.evaluation.failure_classifier import classify_failures
from app.evaluation.metrics import (
    aggregate_metrics,
    build_dataset_breakdown,
    build_failure_analysis,
    build_failure_type_analysis,
    compute_context_precision,
    detect_hallucination,
    evaluate_citations,
    evaluate_retrieval,
    identify_worst_performing,
)
from app.evaluation.schemas import (
    AnswerMatchMode,
    BenchmarkReport,
    BenchmarkRunConfig,
    EvaluationCase,
    EvaluationDataset,
    QuestionResult,
)
from app.ingestion.vector_store.faiss_store import FaissVectorStore
from app.llm.prompt_builder import PromptBuilder
from app.rag.engine import EnterpriseRAG, _build_citations
from app.rag.rbac import check_access, get_accessible_categories, validate_role
from app.rag.router import route_query
from app.rag.types import RetrievalResult
from app.services.rag_service import _create_engine


@dataclass(frozen=True)
class PipelineContext:
    """Initialized production pipeline components for evaluation."""

    settings: Settings
    vector_store: FaissVectorStore
    engine: EnterpriseRAG
    bootstrap: BootstrapResult
    prompt_builder: PromptBuilder


class EvaluationRunner:
    """Run golden dataset cases through the real RAG pipeline."""

    def __init__(
        self,
        *,
        answer_evaluator: AnswerEvaluator | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._answer_evaluator = answer_evaluator or get_answer_evaluator()
        self._prompt_builder = prompt_builder or PromptBuilder()

    def bootstrap_pipeline(
        self,
        config: BenchmarkRunConfig,
    ) -> PipelineContext:
        """Index the evaluation corpus and initialize the production engine."""
        bootstrap = bootstrap_evaluation_corpus(
            corpus_path=config.corpus_path,
            include_documents=config.include_documents,
        )

        settings = get_settings()
        if config.llm_provider_override:
            settings = settings.model_copy(
                update={"llm_provider": config.llm_provider_override}
            )

        engine, _chunk_count = _create_engine(bootstrap.vector_store, settings)
        return PipelineContext(
            settings=settings,
            vector_store=bootstrap.vector_store,
            engine=engine,
            bootstrap=bootstrap,
            prompt_builder=self._prompt_builder,
        )

    def _authorized_sources(self, case: EvaluationCase) -> frozenset[str] | None:
        if case.authorized_sources:
            return frozenset(case.authorized_sources)
        return None

    def _production_retrieval(
        self,
        engine: EnterpriseRAG,
        case: EvaluationCase,
        *,
        top_k: int,
    ) -> list[RetrievalResult]:
        """Run retrieval using the same RBAC path as production."""
        role = validate_role(case.role)
        allowed_categories = set(get_accessible_categories(role))
        return engine._search(
            case.question,
            top_k=top_k,
            allowed_categories=allowed_categories,
            authorized_sources=self._authorized_sources(case),
        )

    def evaluate_case(
        self,
        context: PipelineContext,
        case: EvaluationCase,
        *,
        retrieval_top_k: int,
        default_answer_match_mode: AnswerMatchMode,
        artifacts_dir: Path | None = None,
    ) -> QuestionResult:
        """Evaluate a single golden case through the real pipeline."""
        engine = context.engine
        role = validate_role(case.role)
        route = route_query(case.question)
        access = check_access(role, route.category)

        if not access.allowed:
            empty_retrieval = evaluate_retrieval(case, [], retrieval_top_k=retrieval_top_k)
            answer_eval = self._answer_evaluator.evaluate(
                actual_answer="",
                expected_answer=case.expected_answer,
                mode=case.answer_match_mode or default_answer_match_mode,
            )
            result = QuestionResult(
                case_id=case.id,
                question=case.question,
                difficulty=case.difficulty.value,
                document_type=case.document_type,
                query_category=case.query_category.value,
                tags=list(case.tags),
                retrieval=empty_retrieval,
                answer=answer_eval,
                citation=evaluate_citations(case, []),
                retrieval_latency_ms=0.0,
                generation_latency_ms=0.0,
                total_latency_ms=0.0,
                retrieval_confidence=0.0,
                routed_category=route.category,
                access_granted=False,
                generation_backend="none",
            )
            result.failure_types = classify_failures(case, result)
            return result

        retrieval_started = time.perf_counter()
        retrieval_results = self._production_retrieval(
            engine,
            case,
            top_k=retrieval_top_k,
        )
        retrieval_latency_ms = (time.perf_counter() - retrieval_started) * 1000

        retrieval_eval = evaluate_retrieval(
            case,
            retrieval_results,
            retrieval_top_k=retrieval_top_k,
        )

        generation_started = time.perf_counter()
        prompt_system = ""
        prompt_user = ""
        generated_answer = ""
        citations = []
        retrieval_confidence = 0.0
        generation_backend = "none"

        if not retrieval_results:
            access_granted = True
        else:
            prompt = context.prompt_builder.build(case.question, retrieval_results)
            prompt_system = prompt.system
            prompt_user = prompt.user
            generated = engine._generate_answer(case.question, retrieval_results)
            generated_answer = generated.answer
            citations = _build_citations(retrieval_results)
            retrieval_confidence = generated.retrieval_confidence
            generation_backend = generated.generation_backend
            access_granted = True

        generation_latency_ms = (time.perf_counter() - generation_started) * 1000
        total_latency_ms = retrieval_latency_ms + generation_latency_ms

        answer_mode = case.answer_match_mode or default_answer_match_mode
        answer_eval = self._answer_evaluator.evaluate(
            actual_answer=generated_answer,
            expected_answer=case.expected_answer,
            mode=answer_mode,
        )
        citation_eval = evaluate_citations(case, citations)
        context_precision = compute_context_precision(case, retrieval_results)
        hallucination_detected = detect_hallucination(
            generated_answer,
            retrieval_results,
            expected_answer=case.expected_answer,
        )

        artifact_path: str | None = None
        if artifacts_dir is not None:
            artifact = build_question_artifact(
                case_id=case.id,
                question=case.question,
                expected_answer=case.expected_answer,
                actual_answer=generated_answer,
                retrieval_results=retrieval_results,
                prompt_system=prompt_system,
                prompt_user=prompt_user,
                citations=citations,
                generation_backend=generation_backend,
            )
            saved = save_question_artifact(artifact, artifacts_dir=artifacts_dir)
            artifact_path = str(saved)

        result = QuestionResult(
            case_id=case.id,
            question=case.question,
            difficulty=case.difficulty.value,
            document_type=case.document_type,
            query_category=case.query_category.value,
            tags=list(case.tags),
            retrieval=retrieval_eval,
            answer=answer_eval,
            citation=citation_eval,
            retrieval_latency_ms=round(retrieval_latency_ms, 3),
            generation_latency_ms=round(generation_latency_ms, 3),
            total_latency_ms=round(total_latency_ms, 3),
            retrieval_confidence=retrieval_confidence,
            routed_category=route.category,
            access_granted=access_granted,
            context_precision=context_precision,
            hallucination_detected=hallucination_detected,
            artifact_path=artifact_path,
            generation_backend=generation_backend,
        )
        result.failure_types = classify_failures(
            case,
            result,
            retrieved_chunk_contents=[item.content for item in retrieval_results],
        )
        return result

    def run_dataset(
        self,
        dataset: EvaluationDataset,
        config: BenchmarkRunConfig,
        *,
        dataset_path: str,
        run_id: str | None = None,
        context: PipelineContext | None = None,
    ) -> BenchmarkReport:
        """Execute all dataset cases and return a benchmark report."""
        from datetime import UTC, datetime
        from uuid import uuid4

        started_at = datetime.now(UTC)
        resolved_run_id = run_id or str(uuid4())
        resolved_context = context or self.bootstrap_pipeline(config)

        artifacts_dir: Path | None = None
        if config.capture_artifacts:
            base_dir = Path(config.results_dir) if config.results_dir else (
                Path(__file__).resolve().parents[2] / "evaluation_results"
            )
            artifacts_dir = base_dir / "artifacts" / resolved_run_id

        question_results: list[QuestionResult] = []
        for case in dataset.cases:
            question_results.append(
                self.evaluate_case(
                    resolved_context,
                    case,
                    retrieval_top_k=config.retrieval_top_k,
                    default_answer_match_mode=config.answer_match_mode,
                    artifacts_dir=artifacts_dir,
                )
            )

        completed_at = datetime.now(UTC)
        metrics = aggregate_metrics(
            question_results,
            retrieval_top_k=config.retrieval_top_k,
        )

        metadata = {
            "indexed_documents": resolved_context.bootstrap.indexed_documents,
            "total_chunks": resolved_context.bootstrap.total_chunks,
            "llm_provider": resolved_context.settings.llm_provider,
            "run_label": config.run_label,
            "retrieval_evaluation_method": "semantic",
            "hybrid_enabled": resolved_context.settings.hybrid_enabled,
            "reranking_enabled": resolved_context.settings.reranking_enabled,
            "rerank_model": resolved_context.settings.rerank_model,
            "rerank_top_n": resolved_context.settings.rerank_top_n,
            "query_intelligence_enabled": resolved_context.settings.query_intelligence_enabled,
            "multi_query_enabled": resolved_context.settings.multi_query_enabled,
        }
        if config.embedding_model_id:
            metadata["embedding_model_id"] = config.embedding_model_id
        if resolved_context.bootstrap.embedding_model_name:
            metadata["embedding_model_name"] = resolved_context.bootstrap.embedding_model_name

        return BenchmarkReport(
            run_id=resolved_run_id,
            started_at=started_at,
            completed_at=completed_at,
            dataset_version=dataset.version,
            dataset_path=dataset_path,
            corpus_path=str(resolved_context.bootstrap.corpus_path),
            role=config.role,
            retrieval_top_k=config.retrieval_top_k,
            answer_match_mode=config.answer_match_mode,
            metrics=metrics,
            question_results=question_results,
            failure_analysis=build_failure_analysis(question_results),
            failure_type_analysis=build_failure_type_analysis(question_results),
            dataset_breakdown=build_dataset_breakdown(dataset),
            worst_performing=identify_worst_performing(question_results),
            artifacts_dir=str(artifacts_dir) if artifacts_dir else None,
            metadata=metadata,
        )
