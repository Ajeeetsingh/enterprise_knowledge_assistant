"""Unit tests for User, Role, and user-role relationships."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Role, User

PLACEHOLDER_PASSWORD_HASH = "bcrypt_hash_placeholder_not_plaintext"


def _make_user(
    *,
    email: str = "alice@example.com",
    username: str | None = "alice",
    full_name: str = "Alice Example",
) -> User:
    return User(
        email=email,
        username=username,
        full_name=full_name,
        password_hash=PLACEHOLDER_PASSWORD_HASH,
        is_active=True,
        is_superuser=False,
    )


def _make_role(*, name: str = "Employee", description: str = "Standard access") -> Role:
    return Role(name=name, description=description)


def test_user_model_creation(db_session: Session) -> None:
    user = _make_user()
    db_session.add(user)
    db_session.commit()

    stored = db_session.get(User, user.id)
    assert stored is not None
    assert isinstance(stored.id, uuid.UUID)
    assert stored.email == "alice@example.com"
    assert stored.username == "alice"
    assert stored.full_name == "Alice Example"
    assert stored.password_hash == PLACEHOLDER_PASSWORD_HASH
    assert stored.is_active is True
    assert stored.is_superuser is False
    assert stored.created_at is not None
    assert stored.updated_at is not None


def test_role_model_creation(db_session: Session) -> None:
    role = _make_role(name="HR", description="Human resources")
    db_session.add(role)
    db_session.commit()

    stored = db_session.get(Role, role.id)
    assert stored is not None
    assert stored.name == "HR"
    assert stored.description == "Human resources"
    assert stored.created_at is not None
    assert stored.updated_at is not None


def test_user_role_relationship(db_session: Session) -> None:
    user = _make_user(email="bob@example.com", username="bob")
    admin_role = _make_role(name="Admin", description="Administrator")
    employee_role = _make_role(name="Employee", description="Employee")
    user.roles.extend([admin_role, employee_role])

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert len(user.roles) == 2
    role_names = {role.name for role in user.roles}
    assert role_names == {"Admin", "Employee"}

    db_session.refresh(admin_role)
    assert len(admin_role.users) == 1
    assert admin_role.users[0].email == "bob@example.com"


def test_unique_email_constraint(db_session: Session) -> None:
    db_session.add(_make_user(email="dup@example.com", username="user_a"))
    db_session.commit()

    db_session.add(
        _make_user(email="dup@example.com", username="user_b", full_name="Duplicate")
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_role_name_constraint(db_session: Session) -> None:
    db_session.add(_make_role(name="Finance", description="First"))
    db_session.commit()

    db_session.add(_make_role(name="Finance", description="Duplicate"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
