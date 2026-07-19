"""Reusable API error response models."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error payload returned by the API."""

    detail: str = Field(
        ...,
        description="Human-readable description of the error.",
        examples=["Not authenticated."],
    )
    code: str | None = Field(
        default=None,
        description="Optional stable machine-readable error code.",
        examples=["DUPLICATE_DOCUMENT"],
    )
    existing_document_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "When code is DUPLICATE_DOCUMENT, the public ID of the existing "
            "document if the caller is authorized to access it."
        ),
    )
