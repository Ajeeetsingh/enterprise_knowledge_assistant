"""Knowledge Intelligence Engine (Phase 13.1).

Runs in Shadow Mode alongside the legacy ingestion pipeline. Produces a
canonical ``DocumentKnowledge`` object for each uploaded document without
altering retrieval, API contracts, or the frontend.
"""

from app.knowledge_engine.engine import KnowledgeEngine
from app.knowledge_engine.types import DocumentKnowledge
from app.knowledge_engine.version import KNOWLEDGE_ENGINE_VERSION, PIPELINE_VERSION

__all__ = [
    "DocumentKnowledge",
    "KnowledgeEngine",
    "KNOWLEDGE_ENGINE_VERSION",
    "PIPELINE_VERSION",
]
