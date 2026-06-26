"""Persisted audit helpers for document lifecycle operations (Phase 7.4).

Centralizes document audit event types and metadata shapes.  Document file
contents, embeddings, and checksums must never appear in persisted audit data.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.db.models.document import Document
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.services.audit_service import AuditService, run_persisted_audit


def _build_document_metadata(
    *,
    document_name: str,
    document_type: str | None = None,
    visibility: str | None = None,
    version: int | None = None,
) -> dict[str, Any]:
    """Build document lifecycle metadata from already-loaded fields."""
    metadata: dict[str, Any] = {"document_name": document_name}
    if document_type is not None:
        metadata["document_type"] = document_type
    if visibility is not None:
        metadata["visibility"] = visibility
    if version is not None:
        metadata["version"] = str(version)
    return metadata


def metadata_from_document(document: Document) -> dict[str, Any]:
    """Build audit metadata from a loaded ``Document`` ORM instance."""
    return _build_document_metadata(
        document_name=document.filename,
        document_type=document.content_type,
        visibility=document.visibility,
        version=document.version,
    )


def record_document_uploaded(
    audit_service: AuditService,
    *,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    document_name: str,
    document_type: str | None = None,
    visibility: str | None = None,
    version: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a successful document upload audit event."""
    run_persisted_audit(
        audit_service.log_event(
            event_type="document.uploaded",
            event_category=AuditEventCategory.DOCUMENT,
            action="upload",
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            resource_type="document",
            resource_id=str(document_id),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=_build_document_metadata(
                document_name=document_name,
                document_type=document_type,
                visibility=visibility,
                version=version,
            ),
        )
    )


def record_document_deleted(
    audit_service: AuditService,
    *,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    document_name: str,
    document_type: str | None = None,
    visibility: str | None = None,
    version: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a successful document deletion audit event."""
    run_persisted_audit(
        audit_service.log_event(
            event_type="document.deleted",
            event_category=AuditEventCategory.DOCUMENT,
            action="delete",
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            resource_type="document",
            resource_id=str(document_id),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=_build_document_metadata(
                document_name=document_name,
                document_type=document_type,
                visibility=visibility,
                version=version,
            ),
        )
    )


def record_document_uploaded_from_document(
    audit_service: AuditService,
    *,
    user_id: uuid.UUID,
    document: Document,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist upload audit using fields from a loaded ``Document``."""
    record_document_uploaded(
        audit_service,
        user_id=user_id,
        document_id=document.id,
        document_name=document.filename,
        document_type=document.content_type,
        visibility=document.visibility,
        version=document.version,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def record_document_deleted_from_document(
    audit_service: AuditService,
    *,
    user_id: uuid.UUID,
    document: Document,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist delete audit using fields from a loaded ``Document``."""
    record_document_deleted(
        audit_service,
        user_id=user_id,
        document_id=document.id,
        document_name=document.filename,
        document_type=document.content_type,
        visibility=document.visibility,
        version=document.version,
        ip_address=ip_address,
        user_agent=user_agent,
    )
