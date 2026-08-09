"""Document ORM model for PostgreSQL metadata persistence."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.documents.visibility import DEFAULT_VISIBILITY, DocumentVisibility

if TYPE_CHECKING:
    from app.db.models.knowledge_domain import KnowledgeDomain
    from app.db.models.user import User


class Document(Base):
    """Persisted document metadata including Phase 5.2 security fields.

    Core identity and ingestion columns are unchanged from Phase 4.
    Security metadata added in Phase 5.2:

    - ``department``   — optional owning department (HR, Finance, …)
    - ``owner_id``     — FK to the user who owns (not just uploaded) the doc
    - ``visibility``   — discovery scope: public / restricted / private
    - ``allowed_roles``— JSON-encoded list of role names permitted to access
                         the document when visibility is RESTRICTED

    Storing ``allowed_roles`` as JSON text keeps the schema portable across
    PostgreSQL and SQLite while supporting future migration to a proper
    association table (Phase 5.x ACLs) without changing the column type.

    Active-document uniqueness is tenant-scoped on ``(tenant_id, checksum)``
    so the same file bytes may exist in different organizations, while
    soft-deleted rows do not block re-upload.
    """

    __tablename__ = "documents"
    __table_args__ = (
        Index(
            "uq_documents_tenant_checksum_active",
            "tenant_id",
            "checksum",
            unique=True,
            sqlite_where=text("status != 'deleted' AND tenant_id IS NOT NULL"),
            postgresql_where=text("status != 'deleted' AND tenant_id IS NOT NULL"),
        ),
    )

    # ------------------------------------------------------------------ #
    # Core identity                                                        #
    # ------------------------------------------------------------------ #
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    parent_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="uploaded",
        index=True,
    )
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------ #
    # Phase 5.2 — Security metadata                                        #
    # ------------------------------------------------------------------ #
    department: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    """Optional owning department (e.g. 'HR', 'Finance').

    Used in future phases for department-level authorization filters.
    ``None`` means the document belongs to no specific department.
    """

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    """User who owns (governs) this document.

    Defaults to the uploader at creation time.  Can be reassigned in
    future phases without changing ``uploaded_by``.
    """

    visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DEFAULT_VISIBILITY.value,
        index=True,
    )
    """Discovery scope stored as a plain string value of ``DocumentVisibility``.

    Using a string (not a DB-native enum) keeps the column portable and
    allows new visibility levels to be added without a DDL migration.
    """

    _allowed_roles: Mapped[str | None] = mapped_column(
        "allowed_roles",
        Text,
        nullable=True,
    )
    """JSON-encoded list of role names.

    Stored as ``Text`` so the schema is portable.  Access through the
    ``allowed_roles`` Python property which handles serialization.
    Example raw value: ``'["Admin", "HR"]'``
    """

    # ------------------------------------------------------------------ #
    # Knowledge Domains                                                    #
    # ------------------------------------------------------------------ #
    domain_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_domains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    """FK to the Knowledge Domain this document belongs to.

    Required for new uploads. ``None`` remains valid for legacy documents and
    for admin clear/reassign flows (``ON DELETE SET NULL`` on domain removal).
    """

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    uploader: Mapped[User] = relationship(
        foreign_keys=[uploaded_by],
    )
    owner: Mapped[User | None] = relationship(
        foreign_keys=[owner_id],
    )
    knowledge_domain: Mapped[KnowledgeDomain | None] = relationship(
        back_populates="documents",
        foreign_keys=[domain_id],
    )

    # ------------------------------------------------------------------ #
    # allowed_roles property                                               #
    # ------------------------------------------------------------------ #
    @property
    def allowed_roles(self) -> list[str]:
        """Return the list of allowed role names, or an empty list."""
        if self._allowed_roles is None:
            return []
        try:
            result = json.loads(self._allowed_roles)
            if isinstance(result, list):
                return [str(r) for r in result]
        except (json.JSONDecodeError, TypeError):
            pass
        return []

    @allowed_roles.setter
    def allowed_roles(self, roles: list[str] | None) -> None:
        """Persist *roles* as a JSON string, or ``None`` to clear."""
        if roles is None:
            self._allowed_roles = None
        else:
            self._allowed_roles = json.dumps(sorted(set(roles)))

    # ------------------------------------------------------------------ #
    # Convenience helpers                                                  #
    # ------------------------------------------------------------------ #
    @property
    def visibility_enum(self) -> DocumentVisibility:
        """Return the ``DocumentVisibility`` member for ``self.visibility``."""
        from app.documents.visibility import resolve_visibility
        resolved = resolve_visibility(self.visibility)
        return resolved if resolved is not None else DEFAULT_VISIBILITY
