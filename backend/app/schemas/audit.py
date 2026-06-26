"""Pydantic models for audit log persistence (Phase 7.1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models.audit_log import AuditLog
from app.db.models.enums.audit import AuditEventCategory, AuditStatus

DEFAULT_AUDIT_LIST_LIMIT = 20
MAX_AUDIT_LIST_LIMIT = 100


class AuditLogCreate(BaseModel):
    """Input schema for creating a persisted audit log record."""

    event_type: str = Field(min_length=1, max_length=255)
    event_category: AuditEventCategory
    user_id: uuid.UUID | None = None
    resource_type: str | None = Field(default=None, max_length=100)
    resource_id: str | None = Field(default=None, max_length=255)
    action: str = Field(min_length=1, max_length=255)
    status: AuditStatus
    metadata: dict[str, Any] | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=512)


class AuditLogResponse(BaseModel):
    """Public representation of a persisted audit log record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    event_category: AuditEventCategory
    user_id: uuid.UUID | None
    resource_type: str | None
    resource_id: str | None
    action: str
    status: AuditStatus
    metadata: dict[str, Any] | None = Field(
        validation_alias="event_metadata",
        serialization_alias="metadata",
    )
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    @classmethod
    def from_audit_log(cls, audit_log: AuditLog) -> AuditLogResponse:
        """Build a response from an ORM ``AuditLog`` instance."""
        return cls.model_validate(audit_log, from_attributes=True)


class AuditSearchRequest(BaseModel):
    """Query parameters for searching persisted audit logs."""

    model_config = ConfigDict(extra="forbid")

    event_type: str | None = Field(default=None, max_length=255)
    event_category: AuditEventCategory | None = None
    status: AuditStatus | None = None
    user_id: uuid.UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=DEFAULT_AUDIT_LIST_LIMIT, ge=1, le=MAX_AUDIT_LIST_LIMIT)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_date_range(self) -> AuditSearchRequest:
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("date_from must be before or equal to date_to.")
        return self


class AuditSearchResponse(BaseModel):
    """Paginated audit log search results."""

    items: list[AuditLogResponse]
    total: int
    limit: int
    offset: int
