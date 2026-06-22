"""Unit tests for the RAG integration service layer."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.core.exceptions import RagInitializationError, RagRetrievalError
from app.services.rag_service import (
    RagService,
    _create_engine,
    get_rag_service,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
TEST_DOCUMENTS_PATH = BACKEND_ROOT / "tests" / "fixtures" / "sample_docs"

TEST_SETTINGS = Settings(
    documents_path=TEST_DOCUMENTS_PATH,
    indexes_path=BACKEND_ROOT / "storage" / "indexes",
)


@pytest.fixture(autouse=True)
def clear_rag_service_cache() -> None:
    """Ensure each test gets a fresh cached service instance."""
    get_rag_service.cache_clear()
    yield
    get_rag_service.cache_clear()


@pytest.fixture
def service() -> RagService:
    return RagService(TEST_SETTINGS)


@pytest.fixture
def mock_engine_module(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    """Inject a fake ``app.rag.engine`` module to avoid heavy RAG imports."""
    mock_engine = MagicMock()
    mock_engine.initialize.return_value = 42
    mock_engine.query.return_value = _sample_response()

    mock_engine_cls = MagicMock(return_value=mock_engine)
    fake_module = MagicMock()
    fake_module.EnterpriseRAG = mock_engine_cls

    monkeypatch.setitem(sys.modules, "app.rag.engine", fake_module)
    return mock_engine_cls, mock_engine


def _sample_response() -> MagicMock:
    """Build a stand-in response matching the native RAG shape."""
    response = MagicMock()
    response.answer = "Employees may work remotely up to three days per week."
    return response


def test_service_starts_uninitialized(service: RagService) -> None:
    assert service.is_initialized is False


def test_initialize_loads_engine(
    service: RagService,
    mock_engine_module: tuple[MagicMock, MagicMock],
) -> None:
    mock_engine_cls, mock_engine = mock_engine_module

    chunk_count = service.initialize()

    mock_engine_cls.assert_called_once_with(data_dir=str(TEST_DOCUMENTS_PATH))
    mock_engine.initialize.assert_called_once_with()
    assert chunk_count == 42
    assert service.is_initialized is True


def test_initialize_is_idempotent(
    service: RagService,
    mock_engine_module: tuple[MagicMock, MagicMock],
) -> None:
    mock_engine_cls, mock_engine = mock_engine_module

    first_count = service.initialize()
    second_count = service.initialize()

    mock_engine_cls.assert_called_once()
    mock_engine.initialize.assert_called_once()
    assert first_count == 42
    assert second_count == 42


def test_create_engine_delegates_to_enterprise_rag(
    mock_engine_module: tuple[MagicMock, MagicMock],
) -> None:
    mock_engine_cls, mock_engine = mock_engine_module

    engine, chunk_count = _create_engine(str(TEST_DOCUMENTS_PATH))

    mock_engine_cls.assert_called_once_with(data_dir=str(TEST_DOCUMENTS_PATH))
    mock_engine.initialize.assert_called_once_with()
    assert engine is mock_engine
    assert chunk_count == 42


def test_answer_question_delegates_to_engine(
    service: RagService,
    mock_engine_module: tuple[MagicMock, MagicMock],
) -> None:
    _, mock_engine = mock_engine_module

    response = service.answer_question(
        "What is the remote work policy?",
        "employee",
    )

    mock_engine.query.assert_called_once_with(
        "What is the remote work policy?",
        "employee",
        None,
    )
    assert response.answer.startswith("Employees may work remotely")


def test_answer_question_initializes_once(
    service: RagService,
    mock_engine_module: tuple[MagicMock, MagicMock],
) -> None:
    mock_engine_cls, mock_engine = mock_engine_module

    service.answer_question("First question?", "employee")
    service.answer_question("Second question?", "hr")

    mock_engine_cls.assert_called_once()
    mock_engine.initialize.assert_called_once()
    assert mock_engine.query.call_count == 2


def test_missing_data_directory_raises_initialization_error(
    service: RagService,
    mock_engine_module: tuple[MagicMock, MagicMock],
) -> None:
    _, mock_engine = mock_engine_module
    mock_engine.initialize.side_effect = FileNotFoundError("missing dir")

    with pytest.raises(RagInitializationError, match="data directory"):
        service.answer_question("Any question?", "employee")


def test_empty_knowledge_base_raises_initialization_error(
    service: RagService,
    mock_engine_module: tuple[MagicMock, MagicMock],
) -> None:
    _, mock_engine = mock_engine_module
    mock_engine.initialize.side_effect = ValueError(
        "Cannot build index: no document chunks provided."
    )

    with pytest.raises(RagInitializationError, match="no indexable documents"):
        service.answer_question("Any question?", "employee")


def test_embedding_model_failure_raises_initialization_error(
    service: RagService,
    mock_engine_module: tuple[MagicMock, MagicMock],
) -> None:
    mock_engine_cls, _ = mock_engine_module
    mock_engine_cls.side_effect = OSError("Model download failed")

    with pytest.raises(RagInitializationError, match="Failed to initialize"):
        service.answer_question("Any question?", "employee")


def test_retrieval_failure_raises_retrieval_error(
    service: RagService,
    mock_engine_module: tuple[MagicMock, MagicMock],
) -> None:
    _, mock_engine = mock_engine_module
    mock_engine.initialize.return_value = 10
    mock_engine.query.side_effect = RuntimeError(
        "Index not built. Call build_index() first."
    )

    with pytest.raises(RagRetrievalError, match="index is not available"):
        service.answer_question("Any question?", "employee")


def test_empty_question_raises_value_error(
    service: RagService,
    mock_engine_module: tuple[MagicMock, MagicMock],
) -> None:
    mock_engine_cls, _ = mock_engine_module

    with pytest.raises(ValueError, match="must not be empty"):
        service.answer_question("   ", "employee")

    mock_engine_cls.assert_not_called()


def test_empty_role_raises_value_error(
    service: RagService,
    mock_engine_module: tuple[MagicMock, MagicMock],
) -> None:
    mock_engine_cls, _ = mock_engine_module

    with pytest.raises(ValueError, match="Role must not be empty"):
        service.answer_question("Valid question?", "   ")

    mock_engine_cls.assert_not_called()


def test_get_rag_service_returns_cached_singleton(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.rag_service.get_settings",
        lambda: TEST_SETTINGS,
    )

    first = get_rag_service()
    second = get_rag_service()

    assert first is second
    assert isinstance(first, RagService)
