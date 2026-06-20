"""Document domain — metadata, integrity, and ingestion context types.

Import submodules directly (e.g. ``from app.documents.integrity import ...``)
to avoid eager loading of optional dependency chains.
"""

from app.documents.metadata import DocumentMetadata, IndexingStatus
from app.documents.status import DocumentStatus, DocumentUploadResult
from app.documents.types import IngestionContext, IngestionResult

__all__ = [
    "DocumentMetadata",
    "DocumentStatus",
    "DocumentUploadResult",
    "IndexingStatus",
    "IngestionContext",
    "IngestionResult",
]
