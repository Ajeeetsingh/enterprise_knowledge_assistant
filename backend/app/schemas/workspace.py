"""Workspace summary schemas for the authenticated user dashboard."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceSummaryResponse(BaseModel):
    """Per-user workspace counts for the home dashboard."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "documents_available": 12,
                    "conversations": 4,
                    "questions_asked": 18,
                    "collections": None,
                }
            ]
        }
    )

    documents_available: int = Field(
        ...,
        ge=0,
        description="Documents the current user is authorized to read.",
    )
    conversations: int = Field(
        ...,
        ge=0,
        description="Conversations owned by the current user.",
    )
    questions_asked: int = Field(
        ...,
        ge=0,
        description="User-role messages sent by the current user across conversations.",
    )
    collections: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Collection count when a collections API exists. "
            "Null until collections are persisted server-side."
        ),
    )
