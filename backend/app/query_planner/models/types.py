"""Domain models for Query Planner execution plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class IntentCandidate:
    intent: str
    confidence: float
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedEntity:
    text: str
    kind: str = "unknown"
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QueryConstraints:
    latest: bool = False
    oldest: bool = False
    before: str | None = None
    after: str | None = None
    department: str | None = None
    collection: str | None = None
    document_type: str | None = None
    language: str | None = None
    exact_filename: str | None = None
    partial_filename: str | None = None
    entity_filters: list[str] = field(default_factory=list)
    version_label: str | None = None
    taxonomy_path: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def is_empty(self) -> bool:
        return not any(
            [
                self.latest,
                self.oldest,
                self.before,
                self.after,
                self.department,
                self.collection,
                self.document_type,
                self.language,
                self.exact_filename,
                self.partial_filename,
                self.entity_filters,
                self.version_label,
                self.taxonomy_path,
            ]
        )


@dataclass
class PlannerDiagnostics:
    intent_confusion: list[str] = field(default_factory=list)
    unknown_entities: list[str] = field(default_factory=list)
    missing_indexes: list[str] = field(default_factory=list)
    unsupported_constraints: list[str] = field(default_factory=list)
    planning_failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    timeline_ms: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QueryExecutionPlan:
    """Canonical execution plan — planning only, never retrieval."""

    plan_id: str
    raw_query: str
    normalized_query: str
    intents: list[IntentCandidate] = field(default_factory=list)
    primary_intent: str = "UNKNOWN"
    confidence: float = 0.0
    entities: list[ExtractedEntity] = field(default_factory=list)
    constraints: QueryConstraints = field(default_factory=QueryConstraints)
    required_indexes: list[str] = field(default_factory=list)
    relationship_requirements: list[str] = field(default_factory=list)
    preferred_strategy: str = "Hybrid"
    fallback_strategy: str = "Fallback Hybrid"
    expected_output: str = "documents"
    filters: dict[str, Any] = field(default_factory=dict)
    sort: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostics: PlannerDiagnostics = field(default_factory=PlannerDiagnostics)
    planner_version: str = ""
    created_at: str = ""
    status: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueryExecutionPlan:
        intents = [IntentCandidate(**item) for item in (data.get("intents") or [])]
        entities = [ExtractedEntity(**item) for item in (data.get("entities") or [])]
        constraints_data = data.get("constraints") or {}
        constraints = QueryConstraints(**{
            key: constraints_data.get(key)
            for key in QueryConstraints.__dataclass_fields__
            if key in constraints_data or key in {
                "latest", "oldest", "entity_filters", "extra"
            }
        })
        # Fill defaults for missing keys safely
        constraints = QueryConstraints(
            latest=bool(constraints_data.get("latest", False)),
            oldest=bool(constraints_data.get("oldest", False)),
            before=constraints_data.get("before"),
            after=constraints_data.get("after"),
            department=constraints_data.get("department"),
            collection=constraints_data.get("collection"),
            document_type=constraints_data.get("document_type"),
            language=constraints_data.get("language"),
            exact_filename=constraints_data.get("exact_filename"),
            partial_filename=constraints_data.get("partial_filename"),
            entity_filters=list(constraints_data.get("entity_filters") or []),
            version_label=constraints_data.get("version_label"),
            taxonomy_path=constraints_data.get("taxonomy_path"),
            extra=dict(constraints_data.get("extra") or {}),
        )
        diagnostics_data = data.get("diagnostics") or {}
        diagnostics = PlannerDiagnostics(
            intent_confusion=list(diagnostics_data.get("intent_confusion") or []),
            unknown_entities=list(diagnostics_data.get("unknown_entities") or []),
            missing_indexes=list(diagnostics_data.get("missing_indexes") or []),
            unsupported_constraints=list(diagnostics_data.get("unsupported_constraints") or []),
            planning_failures=list(diagnostics_data.get("planning_failures") or []),
            notes=list(diagnostics_data.get("notes") or []),
            timeline_ms=dict(diagnostics_data.get("timeline_ms") or {}),
        )
        return cls(
            plan_id=str(data.get("plan_id", "")),
            raw_query=str(data.get("raw_query", "")),
            normalized_query=str(data.get("normalized_query", "")),
            intents=intents,
            primary_intent=str(data.get("primary_intent", "UNKNOWN")),
            confidence=float(data.get("confidence") or 0.0),
            entities=entities,
            constraints=constraints,
            required_indexes=list(data.get("required_indexes") or []),
            relationship_requirements=list(data.get("relationship_requirements") or []),
            preferred_strategy=str(data.get("preferred_strategy", "Hybrid")),
            fallback_strategy=str(data.get("fallback_strategy", "Fallback Hybrid")),
            expected_output=str(data.get("expected_output", "documents")),
            filters=dict(data.get("filters") or {}),
            sort=list(data.get("sort") or []),
            warnings=list(data.get("warnings") or []),
            diagnostics=diagnostics,
            planner_version=str(data.get("planner_version", "")),
            created_at=str(data.get("created_at", "")),
            status=str(data.get("status", "ok")),
        )


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
