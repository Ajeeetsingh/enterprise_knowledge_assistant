"""Shared embedding model lifecycle."""

from app.embeddings.manager import EmbeddingModelManager, get_embedding_manager
from app.embeddings.registry import (
    EmbeddingModelSpec,
    EmbeddingRegistryError,
    get_baseline_spec,
    get_model_spec,
    load_embedding_registry,
    resolve_model_specs,
)

__all__ = [
    "EmbeddingModelManager",
    "EmbeddingModelSpec",
    "EmbeddingRegistryError",
    "get_baseline_spec",
    "get_embedding_manager",
    "get_model_spec",
    "load_embedding_registry",
    "resolve_model_specs",
]
