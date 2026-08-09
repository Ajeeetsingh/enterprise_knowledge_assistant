"""Phase 13.8 — Worker Orchestration Framework (Shadow Mode).

Plugin-based orchestration of workers that wrap existing providers.
Not an autonomous AI agent framework.
"""

from app.knowledge_orchestration.orchestrator.orchestrator import KnowledgeOrchestrator
from app.knowledge_orchestration.registry.worker_registry import WorkerRegistry
from app.knowledge_orchestration.version import KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION

__all__ = [
    "KnowledgeOrchestrator",
    "WorkerRegistry",
    "KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION",
]
