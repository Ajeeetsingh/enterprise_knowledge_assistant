"""Audit persistence enums (Phase 7.1).

These enums classify persisted audit log records.  They are stored as plain
``VARCHAR`` columns (via ``StrEnum``) for portability across PostgreSQL and
SQLite — consistent with ``MessageRole`` and ``DocumentVisibility``.
"""

from __future__ import annotations

from enum import StrEnum


class AuditEventCategory(StrEnum):
    """High-level domain category for an audit event."""

    AUTH = "AUTH"
    DOCUMENT = "DOCUMENT"
    CHAT = "CHAT"
    SECURITY = "SECURITY"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class AuditStatus(StrEnum):
    """Outcome status for an audit event."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    WARNING = "WARNING"
