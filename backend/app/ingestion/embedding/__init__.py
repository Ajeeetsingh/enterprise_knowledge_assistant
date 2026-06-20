"""Embedding providers package."""

from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.embedding.sentence_transformer import SentenceTransformerEmbeddingProvider

__all__ = ["EmbeddingProvider", "SentenceTransformerEmbeddingProvider"]
