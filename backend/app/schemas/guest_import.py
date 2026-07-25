"""Authenticated guest-conversation import schemas (untrusted client payload)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.chat import QUESTION_MAX_LENGTH

GUEST_IMPORT_MAX_MESSAGES = 24
GUEST_IMPORT_MAX_MESSAGE_CHARS = max(QUESTION_MAX_LENGTH, 8_000)
GUEST_IMPORT_MAX_TOTAL_CHARS = 48_000
GUEST_IMPORT_DEFAULT_TITLE = "Guest conversation"


class GuestImportMessage(BaseModel):
    """One guest turn to import — role and content only."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(
        ...,
        min_length=1,
        max_length=GUEST_IMPORT_MAX_MESSAGE_CHARS,
    )

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message content must not be empty.")
        return stripped


class GuestImportRequest(BaseModel):
    """Import a temporary guest demo conversation into the authenticated workspace.

    Forbidden client fields (ids, citations, sources, roles, permissions, etc.)
    are rejected via ``extra=\"forbid\"``.
    """

    model_config = ConfigDict(extra="forbid")

    messages: list[GuestImportMessage] = Field(
        ...,
        min_length=1,
        max_length=GUEST_IMPORT_MAX_MESSAGES,
        description="Guest turns in chronological order (oldest → newest).",
    )
    title: str | None = Field(
        default=GUEST_IMPORT_DEFAULT_TITLE,
        max_length=500,
        description="Optional title for the new conversation.",
    )

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return GUEST_IMPORT_DEFAULT_TITLE
        stripped = value.strip()
        return stripped or GUEST_IMPORT_DEFAULT_TITLE

    @model_validator(mode="after")
    def validate_total_size(self) -> GuestImportRequest:
        total = sum(len(item.content) for item in self.messages)
        if total > GUEST_IMPORT_MAX_TOTAL_CHARS:
            raise ValueError(
                f"Imported history exceeds maximum of "
                f"{GUEST_IMPORT_MAX_TOTAL_CHARS} characters."
            )
        return self
