"""Cross-encoder reranking for production retrieval."""

from app.rag.reranking.config import RerankingSettings
from app.rag.reranking.reranker import CrossEncoderReranker
from app.rag.reranking.registry import (
    RerankerModelSpec,
    RerankerRegistryError,
    get_default_spec,
    get_model_spec,
    load_reranker_registry,
)

__all__ = [
    "CrossEncoderReranker",
    "RerankerModelSpec",
    "RerankerRegistryError",
    "RerankingSettings",
    "get_default_spec",
    "get_model_spec",
    "load_reranker_registry",
]
