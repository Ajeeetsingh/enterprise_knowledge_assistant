"""Storage adapter interface — future S3/SharePoint implementations."""

from abc import ABC, abstractmethod
from pathlib import Path


class StorageAdapter(ABC):
    """Abstract file storage adapter."""

    @abstractmethod
    def save(self, relative_path: str, content: bytes) -> Path:
        """Persist raw file content and return the stored path."""

    @abstractmethod
    def delete(self, relative_path: str) -> None:
        """Remove a stored file."""

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """Return True if the file exists."""

    @abstractmethod
    def resolve(self, relative_path: str) -> Path:
        """Return absolute path for a stored file."""
