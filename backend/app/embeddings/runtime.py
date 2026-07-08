"""Evaluation-scoped embedding runtime factories."""

from __future__ import annotations

from dataclasses import dataclass

from app.embeddings.manager import EmbeddingModelManager
from app.embeddings.registry import EmbeddingModelSpec
from app.ingestion.embedding.sentence_transformer import SentenceTransformerEmbeddingProvider
from app.ingestion.vector_store.faiss_store import FaissVectorStore


@dataclass(frozen=True)
class EmbeddingRuntime:
    """Isolated embedding stack for evaluation (does not touch production singleton)."""

    spec: EmbeddingModelSpec
    manager: EmbeddingModelManager
    provider: SentenceTransformerEmbeddingProvider
    vector_store: FaissVectorStore

    @property
    def model_id(self) -> str:
        return self.spec.id

    @property
    def model_name(self) -> str:
        return self.spec.model_name


def create_embedding_runtime(spec: EmbeddingModelSpec) -> EmbeddingRuntime:
    """Create an isolated embedding manager, provider, and vector store for one model."""
    manager = EmbeddingModelManager(model_name=spec.model_name)
    provider = SentenceTransformerEmbeddingProvider(
        model_name=spec.model_name,
        embedding_manager=manager,
    )
    vector_store = FaissVectorStore(
        model_name=spec.model_name,
        embedding_manager=manager,
    )
    return EmbeddingRuntime(
        spec=spec,
        manager=manager,
        provider=provider,
        vector_store=vector_store,
    )
