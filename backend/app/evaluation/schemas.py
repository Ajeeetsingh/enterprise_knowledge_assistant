"""Data models for the retrieval evaluation framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AnswerMatchMode(StrEnum):
    """Supported answer evaluation strategies."""

    EXACT = "exact"
    CASE_INSENSITIVE = "case_insensitive"
    CONTAINS = "contains"
    SEMANTIC = "semantic"


class Difficulty(StrEnum):
    """Benchmark case difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QueryCategory(StrEnum):
    """Query intent categories for benchmark organization."""

    FACTUAL_LOOKUP = "factual_lookup"
    POLICY_RULE = "policy_rule"
    FINANCIAL_DATA = "financial_data"
    PROCEDURE_STEP = "procedure_step"
    SECURITY_REQUIREMENT = "security_requirement"
    COMPLIANCE_RULE = "compliance_rule"
    TABLE_QUERY = "table_query"
    DEFINITION = "definition"
    CROSS_REFERENCE = "cross_reference"
    RBAC_BOUNDARY = "rbac_boundary"


class FailureType(StrEnum):
    """Typed failure classification for post-mortem analysis."""

    RETRIEVAL_FAILURE = "retrieval_failure"
    RANKING_FAILURE = "ranking_failure"
    GENERATION_FAILURE = "generation_failure"
    CITATION_FAILURE = "citation_failure"
    RBAC_FILTERING = "rbac_filtering"
    CONFIDENCE_ISSUE = "confidence_issue"
    TABLE_PARSING = "table_parsing"
    HALLUCINATION = "hallucination"
    CONTEXT_NOISE = "context_noise"


class DocumentType(StrEnum):
    """Enterprise document types represented in the benchmark corpus."""

    OVERVIEW = "overview"
    HANDBOOK = "handbook"
    POLICY = "policy"
    FINANCIAL_REPORT = "financial_report"
    SECURITY_POLICY = "security_policy"
    COMPLIANCE = "compliance"
    PROCEDURE = "procedure"
    LEGAL_POLICY = "legal_policy"
    RISK_FRAMEWORK = "risk_framework"
    BUSINESS_CONTINUITY = "business_continuity"
    PROCUREMENT = "procurement"
    GUIDE = "guide"


@dataclass(frozen=True)
class ExpectedCitation:
    """Expected citation for a benchmark case."""

    source: str
    page: int | None = None


@dataclass(frozen=True)
class EvaluationCase:
    """Single golden evaluation question."""

    id: str
    question: str
    expected_answer: str
    expected_document: str
    expected_page: int | None = None
    expected_page_end: int | None = None
    expected_section_title: str | None = None
    expected_hierarchy_path: tuple[str, ...] = field(default_factory=tuple)
    expected_semantic_region: str | None = None
    expected_chunks: list[int] = field(default_factory=list)
    category: str = "general"
    expected_citations: list[ExpectedCitation] = field(default_factory=list)
    difficulty: Difficulty = Difficulty.MEDIUM
    document_type: str = "general"
    query_category: QueryCategory = QueryCategory.FACTUAL_LOOKUP
    tags: list[str] = field(default_factory=list)
    answer_match_mode: AnswerMatchMode = AnswerMatchMode.CONTAINS
    role: str = "admin"
    authorized_sources: list[str] | None = None
    notes: str | None = None


@dataclass(frozen=True)
class EvaluationDataset:
    """Collection of golden evaluation cases."""

    version: str
    description: str
    cases: list[EvaluationCase]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedChunkDetail:
    """Per-chunk retrieval detail for a single question."""

    rank: int
    chunk_id: str
    chunk_index: int | None
    source: str
    page_number: int | None
    category: str
    confidence: float
    content_preview: str
    semantic_match: bool = False
    match_reasons: list[str] = field(default_factory=list)
    legacy_chunk_match: bool = False


@dataclass
class QuestionArtifact:
    """Per-question capture for post-mortem analysis."""

    case_id: str
    question: str
    expected_answer: str
    actual_answer: str
    prompt_system: str
    prompt_user: str
    retrieved_chunks: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    generation_backend: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "question": self.question,
            "expected_answer": self.expected_answer,
            "actual_answer": self.actual_answer,
            "prompt_system": self.prompt_system,
            "prompt_user": self.prompt_user,
            "retrieved_chunks": self.retrieved_chunks,
            "citations": self.citations,
            "generation_backend": self.generation_backend,
        }


@dataclass
class AnswerEvaluationResult:
    """Outcome of answer evaluation for one case."""

    mode: AnswerMatchMode
    passed: bool
    actual_answer: str
    expected_answer: str
    detail: str


@dataclass
class CitationEvaluationResult:
    """Outcome of citation evaluation for one case."""

    passed: bool
    expected_citations: list[ExpectedCitation]
    actual_citations: list[dict[str, Any]]
    detail: str


@dataclass
class RetrievalEvaluationResult:
    """Per-question retrieval evaluation details."""

    retrieved_documents: list[str]
    retrieved_chunks: list[int]
    retrieved_pages: list[int | None]
    similarity_scores: list[float]
    expected_chunk_found: bool
    expected_rank: int | None
    mrr_contribution: float
    recall_at_1: bool
    recall_at_3: bool
    recall_at_5: bool
    precision_at_k: float
    top_k_details: list[RetrievedChunkDetail]
    failure_reason: str | None = None
    semantic_match_found: bool = False
    evaluation_method: str = "semantic"
    legacy_chunk_match_found: bool = False


@dataclass
class QuestionResult:
    """Complete evaluation outcome for a single question."""

    case_id: str
    question: str
    difficulty: str
    document_type: str
    query_category: str
    tags: list[str]
    retrieval: RetrievalEvaluationResult
    answer: AnswerEvaluationResult
    citation: CitationEvaluationResult
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    retrieval_confidence: float
    routed_category: str
    access_granted: bool
    context_precision: float = 0.0
    hallucination_detected: bool = False
    failure_types: list[FailureType] = field(default_factory=list)
    artifact_path: str | None = None
    generation_backend: str | None = None


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all evaluated questions."""

    case_count: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mrr: float
    precision_at_k: float
    citation_accuracy: float
    answer_accuracy: float
    top_1_correct_pct: float
    top_3_correct_pct: float
    avg_retrieval_confidence: float
    avg_retrieval_latency_ms: float
    avg_generation_latency_ms: float
    avg_total_latency_ms: float
    p50_total_latency_ms: float
    p95_total_latency_ms: float
    context_precision: float
    hallucination_rate: float


@dataclass
class FailureTypeSummary:
    """Aggregated typed failure counts."""

    failure_type: str
    count: int
    case_ids: list[str]


@dataclass
class DatasetBreakdown:
    """Case distribution across dataset dimensions."""

    by_document_type: dict[str, int]
    by_difficulty: dict[str, int]
    by_query_category: dict[str, int]


@dataclass
class FailureSummary:
    """Aggregated failure analysis."""

    failure_reason: str
    count: int
    case_ids: list[str]


@dataclass
class BenchmarkReport:
    """Full benchmark run report."""

    run_id: str
    started_at: datetime
    completed_at: datetime
    dataset_version: str
    dataset_path: str
    corpus_path: str
    role: str
    retrieval_top_k: int
    answer_match_mode: AnswerMatchMode
    metrics: AggregateMetrics
    question_results: list[QuestionResult]
    failure_analysis: list[FailureSummary]
    failure_type_analysis: list[FailureTypeSummary]
    dataset_breakdown: DatasetBreakdown | None
    worst_performing: list[str]
    artifacts_dir: str | None = None
    dashboard_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report to a JSON-compatible dictionary."""

        def _dt(value: datetime) -> str:
            return value.astimezone(UTC).isoformat()

        return {
            "run_id": self.run_id,
            "started_at": _dt(self.started_at),
            "completed_at": _dt(self.completed_at),
            "dataset_version": self.dataset_version,
            "dataset_path": self.dataset_path,
            "corpus_path": self.corpus_path,
            "role": self.role,
            "retrieval_top_k": self.retrieval_top_k,
            "answer_match_mode": self.answer_match_mode.value,
            "metrics": {
                "case_count": self.metrics.case_count,
                "recall_at_1": self.metrics.recall_at_1,
                "recall_at_3": self.metrics.recall_at_3,
                "recall_at_5": self.metrics.recall_at_5,
                "mrr": self.metrics.mrr,
                "precision_at_k": self.metrics.precision_at_k,
                "citation_accuracy": self.metrics.citation_accuracy,
                "answer_accuracy": self.metrics.answer_accuracy,
                "top_1_correct_pct": self.metrics.top_1_correct_pct,
                "top_3_correct_pct": self.metrics.top_3_correct_pct,
                "avg_retrieval_confidence": self.metrics.avg_retrieval_confidence,
                "avg_retrieval_latency_ms": self.metrics.avg_retrieval_latency_ms,
                "avg_generation_latency_ms": self.metrics.avg_generation_latency_ms,
                "avg_total_latency_ms": self.metrics.avg_total_latency_ms,
                "p50_total_latency_ms": self.metrics.p50_total_latency_ms,
                "p95_total_latency_ms": self.metrics.p95_total_latency_ms,
                "context_precision": self.metrics.context_precision,
                "hallucination_rate": self.metrics.hallucination_rate,
            },
            "question_results": [
                {
                    "case_id": result.case_id,
                    "question": result.question,
                    "difficulty": result.difficulty,
                    "document_type": result.document_type,
                    "query_category": result.query_category,
                    "tags": result.tags,
                    "retrieval": {
                        "retrieved_documents": result.retrieval.retrieved_documents,
                        "retrieved_chunks": result.retrieval.retrieved_chunks,
                        "retrieved_pages": result.retrieval.retrieved_pages,
                        "similarity_scores": result.retrieval.similarity_scores,
                        "expected_chunk_found": result.retrieval.expected_chunk_found,
                        "expected_rank": result.retrieval.expected_rank,
                        "mrr_contribution": result.retrieval.mrr_contribution,
                        "recall_at_1": result.retrieval.recall_at_1,
                        "recall_at_3": result.retrieval.recall_at_3,
                        "recall_at_5": result.retrieval.recall_at_5,
                        "precision_at_k": result.retrieval.precision_at_k,
                        "failure_reason": result.retrieval.failure_reason,
                        "semantic_match_found": result.retrieval.semantic_match_found,
                        "evaluation_method": result.retrieval.evaluation_method,
                        "legacy_chunk_match_found": result.retrieval.legacy_chunk_match_found,
                        "top_k_details": [
                            {
                                "rank": detail.rank,
                                "chunk_id": detail.chunk_id,
                                "chunk_index": detail.chunk_index,
                                "source": detail.source,
                                "page_number": detail.page_number,
                                "category": detail.category,
                                "confidence": detail.confidence,
                                "content_preview": detail.content_preview,
                                "semantic_match": detail.semantic_match,
                                "match_reasons": detail.match_reasons,
                                "legacy_chunk_match": detail.legacy_chunk_match,
                            }
                            for detail in result.retrieval.top_k_details
                        ],
                    },
                    "answer": {
                        "mode": result.answer.mode.value,
                        "passed": result.answer.passed,
                        "actual_answer": result.answer.actual_answer,
                        "expected_answer": result.answer.expected_answer,
                        "detail": result.answer.detail,
                    },
                    "citation": {
                        "passed": result.citation.passed,
                        "expected_citations": [
                            {"source": c.source, "page": c.page}
                            for c in result.citation.expected_citations
                        ],
                        "actual_citations": result.citation.actual_citations,
                        "detail": result.citation.detail,
                    },
                    "retrieval_latency_ms": result.retrieval_latency_ms,
                    "generation_latency_ms": result.generation_latency_ms,
                    "total_latency_ms": result.total_latency_ms,
                    "retrieval_confidence": result.retrieval_confidence,
                    "routed_category": result.routed_category,
                    "access_granted": result.access_granted,
                    "context_precision": result.context_precision,
                    "hallucination_detected": result.hallucination_detected,
                    "failure_types": [failure.value for failure in result.failure_types],
                    "artifact_path": result.artifact_path,
                    "generation_backend": result.generation_backend,
                }
                for result in self.question_results
            ],
            "failure_analysis": [
                {
                    "failure_reason": summary.failure_reason,
                    "count": summary.count,
                    "case_ids": summary.case_ids,
                }
                for summary in self.failure_analysis
            ],
            "failure_type_analysis": [
                {
                    "failure_type": summary.failure_type,
                    "count": summary.count,
                    "case_ids": summary.case_ids,
                }
                for summary in self.failure_type_analysis
            ],
            "dataset_breakdown": (
                {
                    "by_document_type": self.dataset_breakdown.by_document_type,
                    "by_difficulty": self.dataset_breakdown.by_difficulty,
                    "by_query_category": self.dataset_breakdown.by_query_category,
                }
                if self.dataset_breakdown is not None
                else None
            ),
            "worst_performing": self.worst_performing,
            "artifacts_dir": self.artifacts_dir,
            "dashboard_path": self.dashboard_path,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class BenchmarkRunConfig:
    """Configuration for a benchmark execution."""

    dataset_path: str | None = None
    corpus_path: str | None = None
    results_dir: str | None = None
    role: str = "admin"
    retrieval_top_k: int = 5
    answer_match_mode: AnswerMatchMode = AnswerMatchMode.CONTAINS
    llm_provider_override: str | None = None
    include_documents: list[str] | None = None
    embedding_model_id: str | None = None
    run_label: str | None = None
    compare_previous: bool = True
    compare_best: bool = True
    capture_artifacts: bool = True
    generate_dashboard: bool = True
