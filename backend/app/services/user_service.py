"""User management business logic."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth.password import hash_password
from app.auth.role_permissions import SystemRole, resolve_system_role
from app.db.models import Role, User


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


class DuplicateUsernameError(UserServiceError):
    def __init__(self) -> None:
        super().__init__("A user with this username already exists.", status_code=409)


class InvalidRoleError(UserServiceError):
    def __init__(self, role_name: str) -> None:
        super().__init__(f"Role '{role_name}' not found.", status_code=404)


class LastAdminError(UserServiceError):
    def __init__(
        self,
        message: str = "Cannot remove the last administrative account.",
    ) -> None:
        super().__init__(message, status_code=400)


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


def _username_exists(
    db: Session,
    username: str,
    *,
    exclude_user_id: uuid.UUID | None = None,
) -> bool:
    query = select(User.id).where(User.username == username)
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    return db.scalar(query) is not None


def is_administrative_user(user: User) -> bool:
    """Return True when *user* holds Admin role or the superuser flag."""
    if user.is_superuser:
        return True
    return any(role.name == SystemRole.ADMIN.value for role in user.roles)


def count_active_admins(db: Session) -> int:
    """Count active users who can administer the platform."""
    users = db.scalars(
        select(User)
        .where(User.is_active.is_(True))
        .options(selectinload(User.roles))
    ).all()
    return sum(1 for user in users if is_administrative_user(user))


def ensure_not_last_admin(db: Session, user: User, *, action: str) -> None:
    """Raise when *action* would leave the installation without an admin."""
    if not is_administrative_user(user):
        return
    if not user.is_active:
        return
    if count_active_admins(db) <= 1:
        raise LastAdminError(
            f"Cannot {action} the last administrative account.",
        )


def _resolve_assignable_role(db: Session, role_name: str) -> Role:
    """Validate *role_name* as a known system role present in the database."""
    resolved = resolve_system_role(role_name)
    if resolved is None:
        raise InvalidRoleError(role_name)
    role = db.scalar(select(Role).where(Role.name == resolved.value))
    if role is None:
        raise InvalidRoleError(resolved.value)
    return role


def create_user_with_role(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    role_name: str,
    username: str | None = None,
) -> User:
    """Create a user and assign *role_name* in a single transaction.

    Rolls back entirely when the role is invalid or uniqueness constraints fail,
    so a loginable roleless account is never persisted.
    """
    role = _resolve_assignable_role(db, role_name)

    if _email_exists(db, email):
        raise DuplicateEmailError()
    if username and _username_exists(db, username):
        raise DuplicateUsernameError()

    user = User(
        email=email,
        username=username,
        full_name=full_name,
        password_hash=hash_password(password),
        is_active=True,
        is_superuser=False,
    )
    user.roles.append(role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if username and _username_exists(db, username):
            raise DuplicateUsernameError() from exc
        raise DuplicateEmailError() from exc

    return get_user(db, user.id)


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    username: str | None = None,
    role: str | None = None,
) -> User:
    """Create a new active user.

    When *role* is provided, creation and role assignment are atomic.
    When omitted, the legacy roleless create path is preserved for callers
    that assign roles separately (prefer ``create_user_with_role``).
    """
    if role is not None:
        return create_user_with_role(
            db,
            email=email,
            password=password,
            full_name=full_name,
            username=username,
            role_name=role,
        )

    if _email_exists(db, email):
        raise DuplicateEmailError()
    if username and _username_exists(db, username):
        raise DuplicateUsernameError()

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
        if username and _username_exists(db, username):
            raise DuplicateUsernameError() from exc
        raise DuplicateEmailError() from exc

    db.refresh(user)
    return get_user(db, user.id)


def register_public_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    username: str | None = None,
) -> User:
    """Self-register a user with the Employee role (server-assigned only)."""
    return create_user_with_role(
        db,
        email=email,
        password=password,
        full_name=full_name,
        username=username,
        role_name=SystemRole.EMPLOYEE.value,
    )


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

    if user.is_active and not is_active:
        ensure_not_last_admin(db, user, action="disable")

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
    ensure_not_last_admin(db, user, action="disable")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return get_user(db, user.id)
