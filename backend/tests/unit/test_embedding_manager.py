"""Tests for shared embedding model manager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.embeddings.manager import EmbeddingModelManager, get_embedding_manager
from app.ingestion.embedding.sentence_transformer import SentenceTransformerEmbeddingProvider
from app.ingestion.vector_store.faiss_store import FaissVectorStore


@pytest.fixture(autouse=True)
def clear_embedding_manager_cache() -> None:
    get_embedding_manager.cache_clear()
    yield
    get_embedding_manager.cache_clear()


def test_get_embedding_manager_returns_singleton() -> None:
    first = get_embedding_manager()
    second = get_embedding_manager()
    assert first is second


def test_faiss_store_and_embedder_share_manager() -> None:
    manager = get_embedding_manager()
    store = FaissVectorStore(embedding_manager=manager)
    embedder = SentenceTransformerEmbeddingProvider(embedding_manager=manager)
    assert store._embedding_manager is manager
    assert embedder._embedding_manager is manager


@patch("sentence_transformers.SentenceTransformer")
def test_model_loaded_once(mock_st_cls: MagicMock) -> None:
    import numpy as np

    mock_model = MagicMock()
    mock_model.get_embedding_dimension.return_value = 384
    mock_model.encode.return_value = np.array([[0.1, 0.2]])
    mock_st_cls.return_value = mock_model

    manager = get_embedding_manager()
    store = FaissVectorStore(embedding_manager=manager)
    embedder = SentenceTransformerEmbeddingProvider(embedding_manager=manager)

    store._load_model()
    embedder.embed(["hello"])
    manager.get_model()

    mock_st_cls.assert_called_once()


@patch("sentence_transformers.SentenceTransformer")
def test_preload_logs_dimension(mock_st_cls: MagicMock) -> None:
    mock_model = MagicMock()
    mock_model.get_embedding_dimension.return_value = 384
    mock_st_cls.return_value = mock_model

    manager = EmbeddingModelManager()
    model = manager.preload()

    assert model is mock_model
    assert manager.is_loaded
    assert manager.dimension == 384


def test_enterprise_rag_does_not_create_retriever_when_using_vector_store() -> None:
    from app.rag.engine import EnterpriseRAG

    store = FaissVectorStore(embedding_manager=get_embedding_manager())
    engine = EnterpriseRAG(vector_store=store)
    assert engine._retriever is None
