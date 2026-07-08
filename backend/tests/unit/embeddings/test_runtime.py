"""Unit tests for evaluation embedding runtime factories."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.embeddings.registry import get_model_spec
from app.embeddings.runtime import create_embedding_runtime


def test_create_embedding_runtime_uses_isolated_manager() -> None:
    spec = get_model_spec("minilm-l6-v2")
    with patch("app.embeddings.runtime.EmbeddingModelManager") as manager_cls:
        manager = MagicMock()
        manager_cls.return_value = manager
        runtime = create_embedding_runtime(spec)

    manager_cls.assert_called_once_with(model_name=spec.model_name)
    assert runtime.spec.id == "minilm-l6-v2"
    assert runtime.provider._embedding_manager is manager
    assert runtime.vector_store._embedding_manager is manager


def test_create_embedding_runtime_dimension_matches_store() -> None:
    spec = get_model_spec("bge-small-en-v1.5")
    runtime = create_embedding_runtime(spec)
    assert runtime.vector_store.model_name == "BAAI/bge-small-en-v1.5"
    assert runtime.manager.model_name == "BAAI/bge-small-en-v1.5"
