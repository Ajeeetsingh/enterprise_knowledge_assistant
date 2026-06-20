"""Reusable API error response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error payload returned by the API."""

    detail: str = Field(
        ...,
        description="Human-readable description of the error.",
        examples=["Not authenticated."],
    )
