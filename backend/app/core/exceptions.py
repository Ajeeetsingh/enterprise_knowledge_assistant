"""Application-wide exception types."""


class EKAError(Exception):
    """Base exception for Enterprise Knowledge Assistant."""


class DatabaseError(EKAError):
    """Raised when a database operation fails."""


class StorageError(EKAError):
    """Raised when a filesystem storage operation fails."""
