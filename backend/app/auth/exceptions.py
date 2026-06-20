"""Authentication-related exceptions."""

from app.core.exceptions import EKAError


class TokenError(EKAError):
    """Base exception for JWT validation failures."""


class TokenExpiredError(TokenError):
    """Raised when a token has expired."""


class TokenInvalidError(TokenError):
    """Raised when a token is malformed or has an invalid signature."""


class TokenTypeError(TokenError):
    """Raised when a token has an unexpected type."""
