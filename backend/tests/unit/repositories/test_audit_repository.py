"""Unit tests for AuditRepository (Phase 7.1)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.constants import TEST_PASSWORD_HASH
from app.db.base import Base
from app.db.models import (  # noqa: F401 — register full model graph
    AuditEventCategory,
    AuditLog,
    AuditStatus,
    Conversation,
    Document,
    Message,
    Role,
    User,
    user_roles,
)
from app.db.repositories.audit_repository import AuditRepository


@pytest.fixture
def db_session() -> Session:
    """Provide a fresh in-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def audit_repo(db_session: Session) -> AuditRepository:
    return AuditRepository(db_session)


@pytest.fixture
def user(db_session: Session) -> User:
    role = Role(name="Admin", description="Administrator")
    u = User(
        id=uuid.uuid4(),
        email="repo-user@example.com",
        username="repouser",
        full_name="Repo User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    u.roles.append(role)
    db_session.add_all([role, u])
    db_session.commit()
    return u


def _create_log(
    repo: AuditRepository,
    *,
    event_type: str,
    category: AuditEventCategory = AuditEventCategory.AUTH,
    status: AuditStatus = AuditStatus.SUCCESS,
    user_id: uuid.UUID | None = None,
) -> AuditLog:
    return repo.create(
        event_type=event_type,
        event_category=category,
        action="test_action",
        status=status,
        user_id=user_id,
    )


class TestAuditRepositoryCreate:
    def test_create_returns_audit_log(
        self, audit_repo: AuditRepository, user: User
    ) -> None:
        log = _create_log(
            audit_repo,
            event_type="auth.login.success",
            user_id=user.id,
        )
        assert isinstance(log, AuditLog)
        assert isinstance(log.id, uuid.UUID)

    def test_create_persists_record(
        self, audit_repo: AuditRepository, db_session: Session
    ) -> None:
        log = _create_log(audit_repo, event_type="system.health.check")
        stored = db_session.get(AuditLog, log.id)
        assert stored is not None
        assert stored.event_type == "system.health.check"


class TestAuditRepositoryGetById:
    def test_get_existing_record(
        self, audit_repo: AuditRepository, user: User
    ) -> None:
        created = _create_log(
            audit_repo,
            event_type="chat.message.sent",
            category=AuditEventCategory.CHAT,
            user_id=user.id,
        )
        found = audit_repo.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id

    def test_get_nonexistent_returns_none(self, audit_repo: AuditRepository) -> None:
        assert audit_repo.get_by_id(uuid.uuid4()) is None


class TestAuditRepositoryListPaginated:
    def test_list_returns_all_records(self, audit_repo: AuditRepository) -> None:
        _create_log(audit_repo, event_type="event.one")
        _create_log(audit_repo, event_type="event.two")
        _create_log(audit_repo, event_type="event.three")

        results, total = audit_repo.list_paginated()
        assert total == 3
        assert len(results) == 3

    def test_list_empty(self, audit_repo: AuditRepository) -> None:
        results, total = audit_repo.list_paginated()
        assert results == []
        assert total == 0

    def test_list_ordered_newest_first(
        self, audit_repo: AuditRepository, db_session: Session
    ) -> None:
        older_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        newer_time = datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

        older = AuditLog(
            id=uuid.uuid4(),
            event_type="older.event",
            event_category=AuditEventCategory.SYSTEM.value,
            action="older",
            status=AuditStatus.SUCCESS.value,
            created_at=older_time,
        )
        newer = AuditLog(
            id=uuid.uuid4(),
            event_type="newer.event",
            event_category=AuditEventCategory.SYSTEM.value,
            action="newer",
            status=AuditStatus.SUCCESS.value,
            created_at=newer_time,
        )
        db_session.add_all([older, newer])
        db_session.commit()

        results, _ = audit_repo.list_paginated()
        ids = [log.id for log in results]
        assert ids.index(newer.id) < ids.index(older.id)

    def test_list_pagination_limit(self, audit_repo: AuditRepository) -> None:
        for index in range(5):
            _create_log(audit_repo, event_type=f"event.{index}")

        results, total = audit_repo.list_paginated(limit=3, offset=0)
        assert total == 5
        assert len(results) == 3

    def test_list_pagination_offset(self, audit_repo: AuditRepository) -> None:
        for index in range(5):
            _create_log(audit_repo, event_type=f"event.{index}")

        results, total = audit_repo.list_paginated(limit=10, offset=3)
        assert total == 5
        assert len(results) == 2

    def test_list_total_reflects_all_records(
        self, audit_repo: AuditRepository
    ) -> None:
        for _ in range(4):
            _create_log(audit_repo, event_type="repeat.event")

        _, total = audit_repo.list_paginated(limit=2, offset=0)
        assert total == 4


class TestAuditRepositorySearch:
    def test_search_filters_by_event_category(
        self, audit_repo: AuditRepository, user: User
    ) -> None:
        audit_repo.create(
            event_type="auth.login.success",
            event_category=AuditEventCategory.AUTH,
            action="login",
            status=AuditStatus.SUCCESS,
            user_id=user.id,
        )
        audit_repo.create(
            event_type="chat.question.asked",
            event_category=AuditEventCategory.CHAT,
            action="ask_question",
            status=AuditStatus.SUCCESS,
            user_id=user.id,
        )

        from app.db.repositories.audit_repository import AuditSearchFilter

        results, total = audit_repo.search(
            filters=AuditSearchFilter(event_category=AuditEventCategory.CHAT),
        )

        assert total == 1
        assert results[0].event_type == "chat.question.asked"

    def test_search_pagination(
        self, audit_repo: AuditRepository, user: User
    ) -> None:
        for index in range(3):
            audit_repo.create(
                event_type=f"event.{index}",
                event_category=AuditEventCategory.SYSTEM,
                action="test",
                status=AuditStatus.SUCCESS,
            )

        page_one, total = audit_repo.search(limit=2, offset=0)
        page_two, _ = audit_repo.search(limit=2, offset=2)

        assert total == 3
        assert len(page_one) == 2
        assert len(page_two) == 1


class TestAuditRepositoryCount:
    def test_count_without_filters(
        self, audit_repo: AuditRepository, user: User
    ) -> None:
        _create_log(audit_repo, event_type="auth.login.success", user_id=user.id)
        _create_log(audit_repo, event_type="chat.question.asked", user_id=user.id)

        assert audit_repo.count() == 2

    def test_count_with_event_type_filter(
        self, audit_repo: AuditRepository, user: User
    ) -> None:
        from app.db.repositories.audit_repository import AuditSearchFilter

        _create_log(audit_repo, event_type="auth.login.failed")
        _create_log(audit_repo, event_type="auth.login.success", user_id=user.id)

        assert audit_repo.count(
            filters=AuditSearchFilter(event_type="auth.login.failed")
        ) == 1
