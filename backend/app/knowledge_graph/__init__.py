"""Phase 13.7 — Knowledge Graph (Shadow Mode).

Typed graph over Knowledge Objects with traversal and expansion services.
Does not perform retrieval, planning, or answer generation.
"""

from app.knowledge_graph.providers.graph_provider import GraphProvider
from app.knowledge_graph.services.graph_service import KnowledgeGraphService
from app.knowledge_graph.version import KNOWLEDGE_GRAPH_PIPELINE_VERSION

__all__ = [
    "GraphProvider",
    "KnowledgeGraphService",
    "KNOWLEDGE_GRAPH_PIPELINE_VERSION",
]
