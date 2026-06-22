"""Shared fixtures for API integration tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.jwt import create_access_token
from app.config import Settings, get_settings
from app.db.base import Base
from app.db.models import Document, Role, User  # noqa: F401 — register models
from app.dependencies import get_db
from app.main import app
from tests.constants import TEST_PASSWORD, TEST_PASSWORD_HASH

TEST_SETTINGS = Settings(
    jwt_secret="integration-test-jwt-secret-key-32bytes-min",
    jwt_algorithm="HS256",
    jwt_access_token_expire_minutes=30,
    jwt_refresh_token_expire_days=7,
)


@pytest.fixture(autouse=True)
def jwt_test_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Use deterministic JWT settings for integration tests."""
    monkeypatch.setenv("JWT_SECRET", TEST_SETTINGS.jwt_secret)
    monkeypatch.setenv("JWT_ALGORITHM", TEST_SETTINGS.jwt_algorithm)
    monkeypatch.setenv(
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        str(TEST_SETTINGS.jwt_access_token_expire_minutes),
    )
    monkeypatch.setenv(
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
        str(TEST_SETTINGS.jwt_refresh_token_expire_days),
    )
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide an isolated in-memory database session per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(scope="session")
def session_client() -> Generator[TestClient, None, None]:
    """Session-scoped TestClient to avoid repeated app lifespan startup."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client(
    db_session: Session,
    session_client: TestClient,
) -> Generator[TestClient, None, None]:
    """FastAPI test client with database dependency override."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield session_client
    app.dependency_overrides.clear()


@pytest.fixture
def employee_role(db_session: Session) -> Role:
    role = Role(name="Employee", description="Standard employee access")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def active_user(db_session: Session, employee_role: Role) -> User:
    user = User(
        email="active@example.com",
        username="active",
        full_name="Active User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(employee_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def access_token_for(user: User) -> str:
    """Build a valid access token for integration tests."""
    return create_access_token(
        user.id,
        user.email,
        [role.name for role in user.roles],
        settings=TEST_SETTINGS,
    )


def bearer_headers(token: str) -> dict[str, str]:
    """Build Authorization headers for integration tests."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_role(db_session: Session) -> Role:
    role = Role(name="Admin", description="Platform administrator")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def hr_role(db_session: Session) -> Role:
    role = Role(name="HR", description="Human resources")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def admin_user(db_session: Session, admin_role: Role) -> User:
    user = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(admin_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def hr_user(db_session: Session, hr_role: Role) -> User:
    user = User(
        email="hr@example.com",
        username="hr",
        full_name="HR User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(hr_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def superuser(db_session: Session, employee_role: Role) -> User:
    user = User(
        email="superuser@example.com",
        username="superuser",
        full_name="Superuser",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
        is_superuser=True,
    )
    user.roles.append(employee_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session: Session, employee_role: Role) -> User:
    user = User(
        email="inactive@example.com",
        username="inactive",
        full_name="Inactive User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=False,
    )
    user.roles.append(employee_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
