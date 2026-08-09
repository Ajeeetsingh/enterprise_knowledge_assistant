"""Phase 13.4 — Hybrid Knowledge Index (Shadow Mode).

Indexes Knowledge Objects (13.1), Registry organization (13.2), and
Relationships (13.3). Never consumed by production retrieval.
"""

from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_index.version import KNOWLEDGE_INDEX_PIPELINE_VERSION

__all__ = ["KnowledgeIndexManager", "KNOWLEDGE_INDEX_PIPELINE_VERSION"]
