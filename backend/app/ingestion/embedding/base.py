"""Embedding provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Generate dense vector embeddings for text.

    The pipeline depends only on this abstraction so providers can be
    swapped without touching pipeline stage code:

    * ``SentenceTransformerEmbeddingProvider`` — local model (MVP)
    * ``OpenAIEmbeddingProvider``              — (future)
    * ``CohereEmbeddingProvider``              — (future)
    * ``VoyageEmbeddingProvider``              — (future)
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text.

        Args:
            texts: Non-empty list of text strings to embed.

        Returns:
            List of float vectors, one per input text, in the same order.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the produced embedding vectors."""
