"""Password hashing and verification using bcrypt via Passlib."""

from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash suitable for storing in ``User.password_hash``."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True when ``plain_password`` matches ``password_hash``."""
    return _pwd_context.verify(plain_password, password_hash)
