"""Unit tests for Phase 5.5 — RetrievalAuthorizationService."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.auth.retrieval_authorization import (
    EMPTY_RETRIEVAL_MESSAGE,
    RetrievalAuthorizationResult,
    RetrievalAuthorizationService,
    log_retrieval_authorization,
)
from app.db.models.document import Document
from app.db.models.role import Role
from app.db.models.user import User
from app.documents.visibility import DocumentVisibility
from app.rag.retriever import RetrievalResult
from tests.constants import TEST_PASSWORD_HASH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(*role_names: str, user_id: uuid.UUID | None = None) -> User:
    user = User(
        id=user_id or uuid.uuid4(),
        email="user@example.com",
        username="testuser",
        full_name="Test User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles = [Role(name=name, description=f"{name} role") for name in role_names]
    return user


def _make_document(
    filename: str,
    *,
    owner_id: uuid.UUID | None = None,
    visibility: DocumentVisibility = DocumentVisibility.RESTRICTED,
    allowed_roles: list[str] | None = None,
) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename=filename,
        content_type="text/plain",
        file_size=100,
        checksum=f"hash-{filename}",
        storage_path=f"docs/{filename}",
        status="searchable",
        uploaded_by=uuid.uuid4(),
        owner_id=owner_id,
        visibility=visibility.value,
    )
    doc.allowed_roles = allowed_roles
    return doc


def _make_result(source: str, category: str = "hr") -> RetrievalResult:
    return RetrievalResult(
        content="Sample content",
        source=source,
        category=category,
        confidence=0.85,
        chunk_id=f"{source}::0",
    )


def _mock_repository(documents: list[Document]) -> MagicMock:
    repo = MagicMock()
    repo.find_by_filenames.return_value = documents
    return repo


# ---------------------------------------------------------------------------
# get_authorized_sources
# ---------------------------------------------------------------------------

class TestGetAuthorizedSources:
    def test_empty_candidates_returns_empty(self) -> None:
        user = _make_user("HR")
        repo = _mock_repository([])
        result = RetrievalAuthorizationService.get_authorized_sources(
            user, frozenset(), repo
        )
        assert result == frozenset()
        repo.find_by_filenames.assert_not_called()

    def test_admin_gets_all_sources(self) -> None:
        user = _make_user("Admin")
        docs = [
            _make_document("public.txt", visibility=DocumentVisibility.PUBLIC),
            _make_document("restricted.txt", visibility=DocumentVisibility.RESTRICTED, allowed_roles=["HR"]),
            _make_document("private.txt", visibility=DocumentVisibility.PRIVATE, owner_id=uuid.uuid4()),
        ]
        repo = _mock_repository(docs)
        candidates = frozenset(d.filename for d in docs)
        result = RetrievalAuthorizationService.get_authorized_sources(user, candidates, repo)
        assert result == candidates

    def test_hr_user_gets_public_and_hr_restricted(self) -> None:
        user = _make_user("HR")
        docs = [
            _make_document("public.txt", visibility=DocumentVisibility.PUBLIC),
            _make_document("hr_only.txt", visibility=DocumentVisibility.RESTRICTED, allowed_roles=["HR"]),
            _make_document("finance_only.txt", visibility=DocumentVisibility.RESTRICTED, allowed_roles=["Finance"]),
            _make_document("private.txt", visibility=DocumentVisibility.PRIVATE, owner_id=uuid.uuid4()),
        ]
        repo = _mock_repository(docs)
        candidates = frozenset(d.filename for d in docs)
        result = RetrievalAuthorizationService.get_authorized_sources(user, candidates, repo)
        assert "public.txt" in result
        assert "hr_only.txt" in result
        assert "finance_only.txt" not in result
        assert "private.txt" not in result

    def test_employee_gets_only_public(self) -> None:
        user = _make_user("Employee")
        docs = [
            _make_document("public.txt", visibility=DocumentVisibility.PUBLIC),
            _make_document("restricted.txt", visibility=DocumentVisibility.RESTRICTED, allowed_roles=["HR"]),
        ]
        repo = _mock_repository(docs)
        candidates = frozenset(d.filename for d in docs)
        result = RetrievalAuthorizationService.get_authorized_sources(user, candidates, repo)
        assert result == frozenset({"public.txt"})

    def test_owner_gets_own_private_document(self) -> None:
        user_id = uuid.uuid4()
        user = _make_user("Employee", user_id=user_id)
        doc = _make_document(
            "my_private.txt",
            owner_id=user_id,
            visibility=DocumentVisibility.PRIVATE,
        )
        repo = _mock_repository([doc])
        result = RetrievalAuthorizationService.get_authorized_sources(
            user, frozenset({"my_private.txt"}), repo
        )
        assert "my_private.txt" in result

    def test_filesystem_only_sources_pass_through(self) -> None:
        """Files without a DB record are not filtered (legacy filesystem docs)."""
        user = _make_user("Employee")
        repo = _mock_repository([])  # No DB records at all
        result = RetrievalAuthorizationService.get_authorized_sources(
            user, frozenset({"filesystem_doc.txt", "another_legacy.txt"}), repo
        )
        # Both should pass through since they have no DB records.
        assert result == frozenset({"filesystem_doc.txt", "another_legacy.txt"})

    def test_single_batch_query_used(self) -> None:
        """Verifies no N+1 DB calls — exactly one find_by_filenames call."""
        user = _make_user("Admin")
        repo = _mock_repository([])
        RetrievalAuthorizationService.get_authorized_sources(
            user,
            frozenset({"a.txt", "b.txt", "c.txt"}),
            repo,
        )
        assert repo.find_by_filenames.call_count == 1

    def test_unknown_visibility_denies_non_admin(self) -> None:
        user = _make_user("HR")
        doc = _make_document("mystery.txt", visibility=DocumentVisibility.PUBLIC)
        doc.visibility = "classified"
        repo = _mock_repository([doc])
        result = RetrievalAuthorizationService.get_authorized_sources(
            user, frozenset({"mystery.txt"}), repo
        )
        assert "mystery.txt" not in result


# ---------------------------------------------------------------------------
# filter_authorized_results
# ---------------------------------------------------------------------------

class TestFilterAuthorizedResults:
    def test_empty_results_returns_empty(self) -> None:
        user = _make_user("HR")
        repo = _mock_repository([])
        auth_result = RetrievalAuthorizationService.filter_authorized_results(
            user, [], repo
        )
        assert auth_result.authorized_results == []
        assert auth_result.candidate_count == 0
        assert auth_result.authorized_count == 0
        assert auth_result.filtered_count == 0

    def test_authorized_results_returned(self) -> None:
        user = _make_user("HR")
        docs = [
            _make_document("hr.txt", visibility=DocumentVisibility.RESTRICTED, allowed_roles=["HR"]),
            _make_document("finance.txt", visibility=DocumentVisibility.RESTRICTED, allowed_roles=["Finance"]),
        ]
        results = [_make_result("hr.txt"), _make_result("finance.txt")]
        repo = _mock_repository(docs)

        auth_result = RetrievalAuthorizationService.filter_authorized_results(
            user, results, repo
        )

        assert auth_result.candidate_count == 2
        assert auth_result.authorized_count == 1
        assert auth_result.filtered_count == 1
        assert auth_result.authorized_results[0].source == "hr.txt"

    def test_all_filtered_returns_empty_list(self) -> None:
        user = _make_user("Employee")
        doc = _make_document(
            "restricted.txt",
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR"],
        )
        results = [_make_result("restricted.txt")]
        repo = _mock_repository([doc])

        auth_result = RetrievalAuthorizationService.filter_authorized_results(
            user, results, repo
        )

        assert auth_result.authorized_results == []
        assert auth_result.filtered_count == 1

    def test_mixed_visibility_collection(self) -> None:
        user = _make_user("Finance")
        docs = [
            _make_document("public.txt", visibility=DocumentVisibility.PUBLIC),
            _make_document("finance.txt", visibility=DocumentVisibility.RESTRICTED, allowed_roles=["Finance"]),
            _make_document("hr.txt", visibility=DocumentVisibility.RESTRICTED, allowed_roles=["HR"]),
            _make_document("private.txt", visibility=DocumentVisibility.PRIVATE, owner_id=uuid.uuid4()),
        ]
        results = [_make_result(d.filename) for d in docs]
        repo = _mock_repository(docs)

        auth_result = RetrievalAuthorizationService.filter_authorized_results(
            user, results, repo
        )

        authorized_sources = {r.source for r in auth_result.authorized_results}
        assert "public.txt" in authorized_sources
        assert "finance.txt" in authorized_sources
        assert "hr.txt" not in authorized_sources
        assert "private.txt" not in authorized_sources

    def test_user_id_in_result(self) -> None:
        user_id = uuid.uuid4()
        user = _make_user("Admin", user_id=user_id)
        repo = _mock_repository([])
        auth_result = RetrievalAuthorizationService.filter_authorized_results(
            user, [], repo
        )
        assert auth_result.user_id == user_id

    def test_query_id_propagated(self) -> None:
        user = _make_user("Admin")
        repo = _mock_repository([])
        auth_result = RetrievalAuthorizationService.filter_authorized_results(
            user, [], repo, query_id="test-qid-123"
        )
        assert auth_result.query_id == "test-qid-123"

    def test_malformed_allowed_roles_handled_safely(self) -> None:
        user = _make_user("HR")
        doc = _make_document(
            "doc.txt",
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=None,
        )
        doc._allowed_roles = "{not valid json"
        results = [_make_result("doc.txt")]
        repo = _mock_repository([doc])

        # Should not raise
        auth_result = RetrievalAuthorizationService.filter_authorized_results(
            user, results, repo
        )
        assert auth_result.filtered_count == 1

    def test_unknown_roles_in_allowed_roles_ignored(self) -> None:
        user = _make_user("HR")
        doc = _make_document(
            "doc.txt",
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR", "bogus_role"],
        )
        results = [_make_result("doc.txt")]
        repo = _mock_repository([doc])

        auth_result = RetrievalAuthorizationService.filter_authorized_results(
            user, results, repo
        )
        # "HR" is valid → granted
        assert auth_result.authorized_count == 1


# ---------------------------------------------------------------------------
# Chunk and citation filtering (via filter_authorized_results)
# ---------------------------------------------------------------------------

class TestChunkFiltering:
    def test_multiple_chunks_from_unauthorized_source_all_filtered(self) -> None:
        user = _make_user("Employee")
        doc = _make_document(
            "hr_policy.txt",
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR"],
        )
        results = [
            _make_result("hr_policy.txt"),
            _make_result("hr_policy.txt"),
            _make_result("hr_policy.txt"),
        ]
        results[1].chunk_id = "hr_policy.txt::1"
        results[2].chunk_id = "hr_policy.txt::2"
        repo = _mock_repository([doc])

        auth_result = RetrievalAuthorizationService.filter_authorized_results(
            user, results, repo
        )
        assert auth_result.authorized_results == []
        assert auth_result.filtered_count == 3

    def test_chunks_from_authorized_source_retained(self) -> None:
        user = _make_user("HR")
        doc = _make_document(
            "hr_policy.txt",
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR"],
        )
        results = [
            RetrievalResult(
                content="chunk 0",
                source="hr_policy.txt",
                category="hr",
                confidence=0.9,
                chunk_id="hr_policy.txt::0",
            ),
            RetrievalResult(
                content="chunk 1",
                source="hr_policy.txt",
                category="hr",
                confidence=0.8,
                chunk_id="hr_policy.txt::1",
            ),
        ]
        repo = _mock_repository([doc])

        auth_result = RetrievalAuthorizationService.filter_authorized_results(
            user, results, repo
        )
        assert len(auth_result.authorized_results) == 2


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------

class TestLogRetrievalAuthorization:
    def test_does_not_raise(self) -> None:
        auth_result = RetrievalAuthorizationResult(
            authorized_results=[],
            candidate_count=5,
            authorized_count=2,
            filtered_count=3,
            user_id=uuid.uuid4(),
            query_id="test-123",
        )
        log_retrieval_authorization(auth_result)  # Should not raise
