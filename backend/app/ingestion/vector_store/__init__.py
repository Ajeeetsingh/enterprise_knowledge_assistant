"""Vector store package."""

from app.ingestion.vector_store.base import VectorStore
from app.ingestion.vector_store.faiss_store import FaissVectorStore

__all__ = ["FaissVectorStore", "VectorStore"]
