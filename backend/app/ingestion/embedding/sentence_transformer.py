"""Sentence-Transformers embedding provider."""

from __future__ import annotations

from app.core.exceptions import EmbeddingError
from app.ingestion.embedding.base import EmbeddingProvider

_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Generate embeddings using a local ``sentence-transformers`` model.

    The model is loaded lazily on the first ``embed()`` call so import time
    remains fast even when ``sentence-transformers`` and ``torch`` are
    installed.
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self._model_name = model_name
        self._model = None  # loaded on first use

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingError(
                    "sentence-transformers is required. "
                    "Install it with: pip install sentence-transformers"
                ) from exc
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            model = self._load_model()
            vectors = model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return [v.tolist() for v in vectors]
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(
                f"Embedding generation failed: {type(exc).__name__}"
            ) from exc

    @property
    def dimension(self) -> int:
        """Return the embedding dimension by loading the model."""
        return len(self.embed(["probe"])[0])
