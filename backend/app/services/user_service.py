"""User management business logic."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth.password import hash_password
from app.db.models import User


class UserServiceError(Exception):
    """Base user service error with an HTTP status code."""

    def __init__(self, message: str, status_code: int) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UserNotFoundError(UserServiceError):
    def __init__(self) -> None:
        super().__init__("User not found.", status_code=404)


class DuplicateEmailError(UserServiceError):
    def __init__(self) -> None:
        super().__init__("A user with this email already exists.", status_code=409)


def _user_query():
    return select(User).options(selectinload(User.roles))


def list_users(db: Session) -> list[User]:
    """Return all users ordered by email."""
    return list(db.scalars(_user_query().order_by(User.email)))


def get_user(db: Session, user_id: uuid.UUID) -> User:
    """Return a single user by ID."""
    user = db.scalar(_user_query().where(User.id == user_id))
    if user is None:
        raise UserNotFoundError()
    return user


def _email_exists(db: Session, email: str, *, exclude_user_id: uuid.UUID | None = None) -> bool:
    query = select(User.id).where(User.email == email)
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    return db.scalar(query) is not None


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    username: str | None = None,
) -> User:
    """Create a new active user with a hashed password."""
    if _email_exists(db, email):
        raise DuplicateEmailError()

    user = User(
        email=email,
        username=username,
        full_name=full_name,
        password_hash=hash_password(password),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateEmailError() from exc

    db.refresh(user)
    return get_user(db, user.id)


def update_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    full_name: str,
    email: str,
    is_active: bool,
) -> User:
    """Update user profile fields. Password is not changed."""
    user = get_user(db, user_id)

    if email != user.email and _email_exists(db, email, exclude_user_id=user_id):
        raise DuplicateEmailError()

    user.full_name = full_name
    user.email = email
    user.is_active = is_active

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateEmailError() from exc

    db.refresh(user)
    return get_user(db, user.id)


def soft_delete_user(db: Session, user_id: uuid.UUID) -> User:
    """Deactivate a user without removing the database row."""
    user = get_user(db, user_id)
    user.is_active = False
    db.commit()
    db.refresh(user)
    return get_user(db, user.id)
