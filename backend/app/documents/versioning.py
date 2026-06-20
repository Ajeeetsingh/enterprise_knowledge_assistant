"""Document versioning foundation — metadata only, no versioning logic yet."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentVersionInfo:
    """Describes a document's position in a future version chain.

    ``version`` starts at 1 for new documents. ``parent_document_id`` links
    a future revision to its predecessor without changing the repository API.
    """

    document_id: uuid.UUID
    version: int
    parent_document_id: uuid.UUID | None
    checksum: str

    @classmethod
    def initial(
        cls,
        *,
        document_id: uuid.UUID,
        checksum: str,
    ) -> DocumentVersionInfo:
        """Build version info for a first-time document upload."""
        return cls(
            document_id=document_id,
            version=1,
            parent_document_id=None,
            checksum=checksum,
        )
