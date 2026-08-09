"""Enterprise Knowledge Registry (Phase 13.2) — Shadow Mode organizational layer."""

from app.knowledge_registry.service import KnowledgeRegistryService
from app.knowledge_registry.types import RegistryEntry, RegistryStatistics
from app.knowledge_registry.version import REGISTRY_PIPELINE_VERSION

__all__ = [
    "KnowledgeRegistryService",
    "RegistryEntry",
    "RegistryStatistics",
    "REGISTRY_PIPELINE_VERSION",
]
