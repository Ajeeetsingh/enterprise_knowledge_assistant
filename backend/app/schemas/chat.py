"""Pydantic models for the chat API public contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

QUESTION_MIN_LENGTH = 1
QUESTION_MAX_LENGTH = 2000


class ChatAskRequest(BaseModel):
    """Request body for submitting a knowledge question."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "How many annual leave days do employees receive?",
                }
            ]
        }
    )

    question: str = Field(
        ...,
        min_length=QUESTION_MIN_LENGTH,
        max_length=QUESTION_MAX_LENGTH,
        description="Natural-language question about enterprise policies or documents.",
        examples=["How many annual leave days do employees receive?"],
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < QUESTION_MIN_LENGTH:
            raise ValueError("Question must not be empty.")
        return stripped


class CitationResponse(BaseModel):
    """A source citation supporting a generated answer."""

    source: str = Field(
        ...,
        description="Source document filename.",
        examples=["hr_policy.txt"],
    )
    excerpt: str = Field(
        ...,
        description="Relevant excerpt from the source document.",
        examples=["Annual leave: 20 days per year for full-time employees."],
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Retrieval confidence score for this citation (0–1).",
        examples=[0.88],
    )


class AnswerResponse(BaseModel):
    """Public API response for a knowledge question."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "answer": "Full-time employees receive 20 annual leave days per year.",
                    "confidence_score": 0.85,
                    "citations": [
                        {
                            "source": "hr_policy.txt",
                            "excerpt": "Annual leave: 20 days per year for full-time employees.",
                            "confidence": 0.88,
                        }
                    ],
                    "message": "Answer generated from hr_policy.txt.",
                }
            ]
        }
    )

    answer: str = Field(
        ...,
        description="Generated answer grounded in retrieved enterprise documents.",
        examples=["Full-time employees receive 20 annual leave days per year."],
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence score for the generated answer (0–1).",
        examples=[0.85],
    )
    citations: list[CitationResponse] = Field(
        default_factory=list,
        description="Source citations used to produce the answer.",
    )
    message: str = Field(
        ...,
        description="Status or contextual message about how the answer was produced.",
        examples=["Answer generated from hr_policy.txt."],
    )
