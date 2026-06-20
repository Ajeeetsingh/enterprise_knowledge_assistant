"""Unit tests for the password security service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.password import hash_password, verify_password
from app.db.models import User

PLAIN_PASSWORD = "Str0ng!Passw0rd"


def test_hash_generation() -> None:
    password_hash = hash_password(PLAIN_PASSWORD)

    assert password_hash
    assert password_hash.startswith("$2")


def test_password_verification() -> None:
    password_hash = hash_password(PLAIN_PASSWORD)

    assert verify_password(PLAIN_PASSWORD, password_hash) is True


def test_wrong_password_rejection() -> None:
    password_hash = hash_password(PLAIN_PASSWORD)

    assert verify_password("WrongPassword!", password_hash) is False


def test_hashes_differ_for_identical_passwords() -> None:
    first_hash = hash_password(PLAIN_PASSWORD)
    second_hash = hash_password(PLAIN_PASSWORD)

    assert first_hash != second_hash
    assert verify_password(PLAIN_PASSWORD, first_hash) is True
    assert verify_password(PLAIN_PASSWORD, second_hash) is True


def test_hash_is_never_equal_to_plain_text() -> None:
    password_hash = hash_password(PLAIN_PASSWORD)

    assert password_hash != PLAIN_PASSWORD


def test_user_model_stores_password_hash(db_session: Session) -> None:
    """Password service integrates with User.password_hash without schema changes."""
    password_hash = hash_password(PLAIN_PASSWORD)
    user = User(
        email="secure@example.com",
        username="secure",
        full_name="Secure User",
        password_hash=password_hash,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.password_hash == password_hash
    assert user.password_hash != PLAIN_PASSWORD
    assert verify_password(PLAIN_PASSWORD, user.password_hash) is True
