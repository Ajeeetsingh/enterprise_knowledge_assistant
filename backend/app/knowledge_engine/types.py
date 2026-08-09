"""Canonical Knowledge Object types for Phase 13.1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SummaryBlock:
    short: str = ""
    detailed: str = ""


@dataclass
class ConfidenceScores:
    overall: float = 0.0
    document_type: float = 0.0
    departments: float = 0.0
    topics: float = 0.0
    keywords: float = 0.0
    entities: float = 0.0
    summary: float = 0.0
    tags: float = 0.0


@dataclass
class ExtractedEntities:
    people: list[str] = field(default_factory=list)
    companies: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    departments: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    policies: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    standards: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    email: list[str] = field(default_factory=list)
    phone: list[str] = field(default_factory=list)
    document_ids: list[str] = field(default_factory=list)

    def total_count(self) -> int:
        return sum(len(getattr(self, name)) for name in self.__dataclass_fields__)


@dataclass
class BasicMetadata:
    filename: str = ""
    extension: str = ""
    page_count: int | None = None
    language: str = "unknown"
    uploader: str | None = None
    upload_date: str | None = None
    owner: str | None = None
    file_size: int = 0


@dataclass
class ProcessingInfo:
    processing_time_ms: float = 0.0
    pipeline_version: str = ""
    model_used: str = "heuristic"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    status: str = "success"


@dataclass
class DocumentKnowledge:
    """Canonical Knowledge Object — foundation for future KIE milestones."""

    document_id: str
    summary: SummaryBlock = field(default_factory=SummaryBlock)
    document_type: str = "Unknown"
    departments: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    entities: ExtractedEntities = field(default_factory=ExtractedEntities)
    tags: list[str] = field(default_factory=list)
    language: str = "unknown"
    confidence: ConfidenceScores = field(default_factory=ConfidenceScores)
    metadata: BasicMetadata = field(default_factory=BasicMetadata)
    processing_info: ProcessingInfo = field(default_factory=ProcessingInfo)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentKnowledge:
        summary = SummaryBlock(**(data.get("summary") or {}))
        confidence = ConfidenceScores(**(data.get("confidence") or {}))
        entities = ExtractedEntities(**(data.get("entities") or {}))
        metadata = BasicMetadata(**(data.get("metadata") or {}))
        processing_info = ProcessingInfo(**(data.get("processing_info") or {}))
        return cls(
            document_id=str(data.get("document_id", "")),
            summary=summary,
            document_type=str(data.get("document_type", "Unknown")),
            departments=list(data.get("departments") or []),
            topics=list(data.get("topics") or []),
            keywords=list(data.get("keywords") or []),
            entities=entities,
            tags=list(data.get("tags") or []),
            language=str(data.get("language", "unknown")),
            confidence=confidence,
            metadata=metadata,
            processing_info=processing_info,
        )


@dataclass(frozen=True)
class KnowledgeAnalysisRequest:
    """Input for a single Knowledge Engine analysis run."""

    document_id: str
    filename: str
    content_type: str
    file_size: int
    text: str
    uploader: str | None = None
    owner: str | None = None
    upload_date: str | None = None
    department_hint: str | None = None
