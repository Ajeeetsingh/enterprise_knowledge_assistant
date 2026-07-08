"""Sentence-Transformers embedding provider."""

from __future__ import annotations

from app.core.exceptions import EmbeddingError
from app.embeddings.manager import EmbeddingModelManager, get_embedding_manager
from app.ingestion.embedding.base import EmbeddingProvider
from app.rag.types import EMBEDDING_MODEL_NAME


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Generate embeddings using the shared sentence-transformers model."""

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        embedding_manager: EmbeddingModelManager | None = None,
    ) -> None:
        self._model_name = model_name
        self._embedding_manager = embedding_manager or get_embedding_manager()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = self._embedding_manager.encode(texts)
            return [v.tolist() for v in vectors]
        except EmbeddingError:
            raise
        except RuntimeError as exc:
            raise EmbeddingError(str(exc)) from exc
        except Exception as exc:
            raise EmbeddingError(
                f"Embedding generation failed: {type(exc).__name__}"
            ) from exc

    @property
    def dimension(self) -> int:
        """Return the embedding dimension from the shared model."""
        return self._embedding_manager.dimension
