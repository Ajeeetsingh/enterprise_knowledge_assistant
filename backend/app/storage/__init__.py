"""File storage abstraction."""

from app.storage.interface import StorageAdapter
from app.storage.local import LocalStorage

__all__ = ["LocalStorage", "StorageAdapter"]
