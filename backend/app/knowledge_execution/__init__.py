"""Phase 13.6 — Knowledge Execution Engine (Shadow Mode).

Consumes QueryExecutionPlans and produces CandidateEvidenceSet artifacts.
Never calls FAISS, BM25, reranker, or LLM.
"""

from app.knowledge_execution.coordinators.coordinator import ExecutionCoordinator
from app.knowledge_execution.executor.engine import KnowledgeExecutionEngine
from app.knowledge_execution.version import KNOWLEDGE_EXECUTION_PIPELINE_VERSION

__all__ = [
    "ExecutionCoordinator",
    "KnowledgeExecutionEngine",
    "KNOWLEDGE_EXECUTION_PIPELINE_VERSION",
]
