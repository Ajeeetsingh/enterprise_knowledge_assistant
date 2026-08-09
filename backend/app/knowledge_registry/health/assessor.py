"""Knowledge health assessment."""

from __future__ import annotations

from app.knowledge_engine.types import DocumentKnowledge
from app.knowledge_registry.enums import KnowledgeHealthStatus
from app.knowledge_registry.types import RegistryEntry


class HealthAssessor:
    """Assign a health status and manual-review flags."""

    def assess(
        self,
        knowledge: DocumentKnowledge,
        entry: RegistryEntry,
        *,
        is_latest_in_group: bool = True,
    ) -> tuple[str, bool, list[str]]:
        filename = (knowledge.metadata.filename or "").lower()
        reasons: list[str] = []

        if entry.probable_duplicate_of and entry.duplicate_score >= 0.9:
            return KnowledgeHealthStatus.DUPLICATE.value, True, ["probable_duplicate"]

        if "archived" in filename or "archive" in filename:
            return KnowledgeHealthStatus.ARCHIVED.value, False, []

        if "draft" in filename:
            return KnowledgeHealthStatus.DRAFT.value, True, ["draft_marker"]

        if entry.primary_collection == "external" or "External" in knowledge.departments:
            return KnowledgeHealthStatus.EXTERNAL.value, False, []

        if not is_latest_in_group and entry.version_group_key:
            return KnowledgeHealthStatus.SUPERSEDED.value, False, ["older_version"]

        incomplete = False
        if not knowledge.summary.short or knowledge.document_type == "Unknown":
            incomplete = True
            reasons.append("missing_summary_or_type")
        if knowledge.confidence.overall < 0.45:
            incomplete = True
            reasons.append("low_confidence")
        if not entry.collections or entry.primary_collection == "unknown":
            incomplete = True
            reasons.append("missing_collection")
        if incomplete:
            return KnowledgeHealthStatus.INCOMPLETE.value, True, reasons

        if knowledge.confidence.overall >= 0.78 and entry.taxonomy_path and not reasons:
            return KnowledgeHealthStatus.VERIFIED.value, False, []

        if knowledge.confidence.overall >= 0.6:
            return KnowledgeHealthStatus.HEALTHY.value, False, []

        return KnowledgeHealthStatus.UNKNOWN.value, True, ["ambiguous_health"]
