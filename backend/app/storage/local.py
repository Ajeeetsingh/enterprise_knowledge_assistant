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
        """Resolve *relative_path* and ensure it stays under ``base_path``.

        Accepts a relative storage key or an absolute path already under the
        storage root (legacy rows). Rejects ``..`` traversal and paths that
        resolve outside the storage root (avoids ``startswith`` prefix bypass).
        """
        if not relative_path or not str(relative_path).strip():
            raise StorageError("Invalid storage path: empty path.")

        base = self.base_path.resolve()
        raw = Path(relative_path)

        if raw.is_absolute():
            destination = raw.resolve()
        else:
            if ".." in raw.parts:
                raise StorageError(f"Invalid storage path: {relative_path}")
            destination = (base / relative_path).resolve()

        try:
            destination.relative_to(base)
        except ValueError as exc:
            raise StorageError(f"Invalid storage path: {relative_path}") from exc
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
