"""Pydantic models for the Knowledge Domains API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models.knowledge_domain import KnowledgeDomain


class KnowledgeDomainCreateRequest(BaseModel):
    """Request body for creating a knowledge domain."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Procurement",
                    "description": "Sourcing and vendor management policies.",
                }
            ]
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Unique domain name.",
        examples=["Procurement"],
    )
    description: str | None = Field(
        default=None,
        description="Optional domain description.",
        examples=["Sourcing and vendor management policies."],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Domain name must not be empty.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class KnowledgeDomainResponse(BaseModel):
    """Public representation of a knowledge domain."""

    id: uuid.UUID
    name: str
    description: str | None

    @classmethod
    def from_domain(cls, domain: KnowledgeDomain) -> KnowledgeDomainResponse:
        return cls(
            id=domain.id,
            name=domain.name,
            description=domain.description,
        )


class KnowledgeDomainListResponse(BaseModel):
    """List wrapper for knowledge domains."""

    items: list[KnowledgeDomainResponse]
