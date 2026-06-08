"""Local filesystem storage adapter (MVP)."""

from pathlib import Path

from app.config import get_settings
from app.core.exceptions import StorageError
from app.storage.interface import StorageAdapter


class LocalStorage(StorageAdapter):
    """Store files on the local filesystem under backend/storage/documents/."""

    def __init__(self, base_path: Path | None = None) -> None:
        settings = get_settings()
        self.base_path = base_path or settings.documents_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative_path: str) -> Path:
        destination = (self.base_path / relative_path).resolve()
        if not str(destination).startswith(str(self.base_path.resolve())):
            raise StorageError(f"Invalid storage path: {relative_path}")
        return destination

    def save(self, relative_path: str, content: bytes) -> Path:
        path = self._safe_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def delete(self, relative_path: str) -> None:
        path = self._safe_path(relative_path)
        if path.exists():
            path.unlink()

    def exists(self, relative_path: str) -> bool:
        return self._safe_path(relative_path).exists()

    def resolve(self, relative_path: str) -> Path:
        return self._safe_path(relative_path)
