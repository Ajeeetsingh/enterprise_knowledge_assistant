"""Public guest/demo ask schemas (no authentication, no document access)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.chat import QUESTION_MAX_LENGTH, QUESTION_MIN_LENGTH

GUEST_HISTORY_MAX_MESSAGES = 6
GUEST_HISTORY_MAX_MESSAGE_CHARS = 2_000
GUEST_HISTORY_MAX_TOTAL_CHARS = 6_000


class GuestHistoryMessage(BaseModel):
    """One prior guest turn supplied by the client (not trusted beyond bounds)."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=GUEST_HISTORY_MAX_MESSAGE_CHARS)
    answer_kind: str | None = Field(
        default=None,
        max_length=64,
        description="Optional prior assistant answer kind for follow-up routing.",
    )

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("History message content must not be empty.")
        return stripped


class GuestAskRequest(BaseModel):
    """Public guest demo question — forbid client-supplied identity or ACL fields."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(
        ...,
        min_length=QUESTION_MIN_LENGTH,
        max_length=QUESTION_MAX_LENGTH,
        description="Guest question for the public demo assistant.",
    )
    history: list[GuestHistoryMessage] = Field(
        default_factory=list,
        max_length=GUEST_HISTORY_MAX_MESSAGES,
        description="Bounded recent guest turns (oldest → newest).",
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < QUESTION_MIN_LENGTH:
            raise ValueError("Question must not be empty.")
        return stripped

    @model_validator(mode="after")
    def validate_history_budget(self) -> GuestAskRequest:
        total = sum(len(item.content) for item in self.history)
        if total > GUEST_HISTORY_MAX_TOTAL_CHARS:
            raise ValueError(
                f"History exceeds maximum of {GUEST_HISTORY_MAX_TOTAL_CHARS} characters."
            )
        return self


class GuestAskResponse(BaseModel):
    """Public guest demo answer — never includes citations or document sources."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    message: str = ""
    answer_kind: str | None = None
    requires_auth: bool = False
