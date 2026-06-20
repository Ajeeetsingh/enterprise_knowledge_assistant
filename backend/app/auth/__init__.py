"""Authentication module."""

from app.auth.exceptions import (
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    TokenTypeError,
)
from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)
from app.auth.authorization import require_any_role, require_role, require_superuser
from app.auth.password import hash_password, verify_password
from app.auth.security import get_current_user

__all__ = [
    "get_current_user",
    "require_any_role",
    "require_role",
    "require_superuser",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenTypeError",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "verify_password",
    "verify_token",
]
