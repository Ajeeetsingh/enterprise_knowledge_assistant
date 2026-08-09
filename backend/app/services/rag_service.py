"""RAG integration service — sole bridge between the backend and the RAG engine."""

from __future__ import annotations

import logging
import threading
from functools import lru_cache
from typing import TYPE_CHECKING

from app.config import Settings, get_settings
from app.core.exceptions import (
    EmbeddingError,
    RagInitializationError,
    RagRetrievalError,
    RagServiceError,
)
from app.core.logging import get_logger, log_with_fields

if TYPE_CHECKING:
    from app.ingestion.vector_store.faiss_store import FaissVectorStore
    from app.rag.engine import EnterpriseRAG
    from app.rag.types import QueryResponse

logger = get_logger(__name__)


def _create_engine(vector_store: "FaissVectorStore", settings: Settings) -> tuple["EnterpriseRAG", int]:
    """Construct and initialize the RAG engine against the shared vector store."""
    from app.llm.factory import create_llm_provider
    from app.rag.engine import EnterpriseRAG

    llm_provider = create_llm_provider(settings)
    engine = EnterpriseRAG(
        vector_store=vector_store,
        llm_provider=llm_provider,
        llm_fallback_enabled=settings.llm_fallback_enabled,
    )
    chunk_count = engine.initialize()
    return engine, chunk_count


class RagService:
    """Integration layer wrapping the production-tested EnterpriseRAG engine."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: EnterpriseRAG | None = None
        self._initialized = False
        self._chunk_count = 0
        self._init_lock = threading.Lock()

    @property
    def is_initialized(self) -> bool:
        """Return whether the underlying RAG engine has been initialized."""
        return self._initialized

    def initialize(self) -> int:
        """Attach to the shared vector store used by document ingestion.

        Idempotent — subsequent calls return without re-initializing.
        Returns the number of indexed document chunks.
        """
        if self._engine is not None and self._initialized:
            return self._chunk_count

        with self._init_lock:
            if self._engine is not None and self._initialized:
                return self._chunk_count

            from app.services.document_service import get_document_service

            vector_store = get_document_service().vector_store
            log_with_fields(
                logger,
                logging.INFO,
                "RAG initialization started",
                vector_store_size=vector_store.size,
                indexes_path=str(self._settings.indexes_path),
            )

            try:
                engine, chunk_count = _create_engine(vector_store, self._settings)
            except ValueError as exc:
                message = str(exc).lower()
                if "no document chunks" in message or "cannot build index" in message:
                    log_with_fields(
                        logger,
                        logging.ERROR,
                        "RAG initialization failed",
                        reason="empty_knowledge_base",
                    )
                    raise RagInitializationError(
                        "Knowledge base contains no indexable documents."
                    ) from exc
                log_with_fields(
                    logger,
                    logging.ERROR,
                    "RAG initialization failed",
                    reason="invalid_configuration",
                )
                raise RagInitializationError(
                    "Failed to initialize the knowledge retrieval engine."
                ) from exc
            except EmbeddingError as exc:
                log_with_fields(
                    logger,
                    logging.ERROR,
                    "RAG initialization failed",
                    reason="embedding_provider_unavailable",
                )
                raise RagInitializationError(
                    "Failed to initialize the knowledge retrieval engine."
                ) from exc
            except Exception as exc:
                log_with_fields(
                    logger,
                    logging.ERROR,
                    "RAG initialization failed",
                    reason=type(exc).__name__,
                )
                raise RagInitializationError(
                    "Failed to initialize the knowledge retrieval engine."
                ) from exc

            log_with_fields(
                logger,
                logging.INFO,
                "RAG initialization succeeded",
                chunk_count=chunk_count,
                vector_store_size=vector_store.size,
            )
            self._engine = engine
            self._initialized = True
            self._chunk_count = chunk_count
            return chunk_count

    def _ensure_initialized(self) -> EnterpriseRAG:
        """Return the initialized engine, initializing on first use."""
        if self._engine is None or not self._initialized:
            self.initialize()
        assert self._engine is not None
        return self._engine

    def answer_question(
        self,
        question: str,
        role: str,
        authorized_sources: frozenset[str] | None = None,
        *,
        conversation_history: str | None = None,
    ) -> "QueryResponse":
        """Run a natural-language query through the RAG engine."""
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("Question must not be empty.")

        normalized_role = role.strip()
        if not normalized_role:
            raise ValueError("Role must not be empty.")

        engine = self._ensure_initialized()

        try:
            from app.rag.observability.collector import get_active_trace, trace_question

            diagnostics_on = bool(
                getattr(self._settings, "rag_diagnostics_enabled", False)
            )
            # If a caller already opened a trace (e.g. offline script), reuse it.
            if get_active_trace() is not None or not diagnostics_on:
                return engine.query(
                    normalized_question,
                    normalized_role,
                    authorized_sources,
                    conversation_history=conversation_history,
                )
            with trace_question(normalized_question):
                return engine.query(
                    normalized_question,
                    normalized_role,
                    authorized_sources,
                    conversation_history=conversation_history,
                )
        except RuntimeError as exc:
            message = str(exc).lower()
            if "index not built" in message or "not initialized" in message:
                log_with_fields(
                    logger,
                    logging.ERROR,
                    "RAG retrieval failed",
                    reason="index_unavailable",
                )
                raise RagRetrievalError(
                    "Knowledge retrieval index is not available."
                ) from exc
            log_with_fields(
                logger,
                logging.ERROR,
                "RAG retrieval failed",
                reason="runtime_error",
            )
            raise RagRetrievalError("Knowledge retrieval failed.") from exc
        except RagServiceError:
            raise
        except Exception as exc:
            log_with_fields(
                logger,
                logging.ERROR,
                "RAG retrieval failed",
                reason=type(exc).__name__,
            )
            raise RagRetrievalError("Knowledge retrieval failed.") from exc


@lru_cache
def get_rag_service() -> RagService:
    """Return a cached RAG service instance."""
    return RagService(get_settings())
