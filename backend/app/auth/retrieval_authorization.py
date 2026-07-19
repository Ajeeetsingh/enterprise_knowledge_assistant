"""Retrieval-level authorization for the RAG pipeline (Phase 5.5).

Determines which source documents a user may receive as retrieval results
before those results reach the LLM.  Authorization decisions are delegated
entirely to ``DocumentAuthorizationService`` — no duplicate logic lives here.

Architecture note
-----------------
The RAG pipeline indexes filesystem documents and identifies each chunk by
its source *filename*.  The Document DB tracks uploaded files with full
security metadata (visibility, owner, allowed_roles).

This service bridges the two systems:

1.  Given a set of candidate filenames from a vector search candidate set,
    look up their DB records in **one batch query** (no N+1 lookups).
2.  Apply ``DocumentAuthorizationService`` to every DB-resident document.
3.  Filenames with **no DB record** are treated as legacy/filesystem-only
    documents — they bypass document-level auth and are gated only by the
    existing category-based RBAC already in place.
4.  Return the set of authorized filenames so the retriever can constrain
    its FAISS search to authorized chunks only.

``DocumentAuthorizationService`` remains the **single source of truth** for
all authorization decisions.  This service only orchestrates the lookup and
batch filtering.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.audit.service import AuditService
from app.auth.document_authorization import DocumentAuthorizationService
from app.core.logging import get_logger
from app.db.models.user import User
from app.db.repositories.document_repository import DocumentRepository
from app.rag.types import RetrievalResult

logger = get_logger(__name__)

EMPTY_RETRIEVAL_MESSAGE = (
    "I couldn't find any information that you are authorized to access."
)


@dataclass(frozen=True)
class RetrievalAuthorizationResult:
    """Summary of a retrieval authorization pass.

    Attributes:
        authorized_results: Filtered list of retrieval results the user
            may receive.
        candidate_count: Total candidate results before filtering.
        authorized_count: Results retained after authorization.
        filtered_count: Results removed by authorization.
        user_id: UUID of the requesting user.
        query_id: Optional caller-supplied query identifier.
    """

    authorized_results: list[RetrievalResult]
    candidate_count: int
    authorized_count: int
    filtered_count: int
    user_id: uuid.UUID
    query_id: str | None = None


class RetrievalAuthorizationService:
    """Filter RAG retrieval results to only those the user may access.

    This class has no state.  All methods are static so it can be used
    without instantiation from routes and service layers alike.

    Design principles
    -----------------
    * Batch DB lookup — a single ``IN`` query resolves all candidate
      filenames; no per-result database round-trips.
    * Cached role evaluation — ``get_user_system_roles`` is called once
      and reused across all document checks in the same request.
    * Fail-closed for unknown visibility — delegated to
      ``DocumentAuthorizationService._evaluate``.
    * Transparent for filesystem-only sources — documents absent from
      the DB are denied (fail closed — orphan index sources must not leak).
    * Never modifies stored metadata — read-only access to the repository.
    """

    @staticmethod
    def get_authorized_sources(
        user: User,
        candidate_sources: frozenset[str],
        repository: DocumentRepository,
        *,
        query_id: str | None = None,
    ) -> frozenset[str]:
        """Return the subset of *candidate_sources* the user is allowed to read.

        Sources with no matching DB record are denied (fail closed). Index
        entries must correspond to persisted document metadata for access
        control to apply; orphan/legacy filenames are never auto-authorized.

        Args:
            user: Authenticated requesting user.
            candidate_sources: Filenames from the RAG candidate pool.
            repository: Document repository for batch metadata lookup.
            query_id: Optional identifier for log correlation.

        Returns:
            Frozen set of source filenames the user is authorized to access.
        """
        if not candidate_sources:
            return frozenset()

        # Single batch query — no N+1 lookups.
        db_documents = repository.find_by_filenames(list(candidate_sources))
        db_by_filename: dict[str, object] = {doc.filename: doc for doc in db_documents}

        authorized: set[str] = set()

        for source in candidate_sources:
            document = db_by_filename.get(source)
            if document is None:
                # Fail closed: unknown/orphan index sources are not readable.
                continue

            decision = DocumentAuthorizationService.can_read_document(user, document)  # type: ignore[arg-type]
            if decision.granted:
                authorized.add(source)

        return frozenset(authorized)

    @staticmethod
    def filter_authorized_results(
        user: User,
        results: list[RetrievalResult],
        repository: DocumentRepository,
        *,
        query_id: str | None = None,
    ) -> RetrievalAuthorizationResult:
        """Filter *results* to only those from authorized document sources.

        Args:
            user: Authenticated requesting user.
            results: Candidate retrieval results from the vector search.
            repository: Document repository for batch metadata lookup.
            query_id: Optional identifier for log correlation.

        Returns:
            ``RetrievalAuthorizationResult`` containing the filtered list
            and summary counts for structured logging.
        """
        candidate_count = len(results)

        if not results:
            return RetrievalAuthorizationResult(
                authorized_results=[],
                candidate_count=0,
                authorized_count=0,
                filtered_count=0,
                user_id=user.id,
                query_id=query_id,
            )

        candidate_sources = frozenset(r.source for r in results)
        authorized_sources = RetrievalAuthorizationService.get_authorized_sources(
            user,
            candidate_sources,
            repository,
            query_id=query_id,
        )

        authorized_results = [r for r in results if r.source in authorized_sources]
        authorized_count = len(authorized_results)
        filtered_count = candidate_count - authorized_count

        return RetrievalAuthorizationResult(
            authorized_results=authorized_results,
            candidate_count=candidate_count,
            authorized_count=authorized_count,
            filtered_count=filtered_count,
            user_id=user.id,
            query_id=query_id,
        )


def log_retrieval_authorization(
    auth_result: RetrievalAuthorizationResult,
) -> None:
    """Emit a structured audit event summarising the retrieval authorization pass.

    Emits a ``RAG_RETRIEVAL_FILTERED`` event when documents were removed.

    Args:
        auth_result: The result object returned by
            ``RetrievalAuthorizationService.filter_authorized_results``.
    """
    if auth_result.filtered_count > 0:
        AuditService.record(
            AuditService.rag_retrieval_filtered(
                user_id=str(auth_result.user_id),
                query_id=auth_result.query_id,
                candidate_count=auth_result.candidate_count,
                authorized_count=auth_result.authorized_count,
                filtered_count=auth_result.filtered_count,
            )
        )
