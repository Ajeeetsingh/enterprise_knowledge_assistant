"""Structure kinds detected on retrieved evidence (Phase 4B)."""

from __future__ import annotations

from enum import Enum


class EvidenceStructureKind(str, Enum):
    """Enterprise structures inferred from retrieved metadata/content signals."""

    DEFINITION = "definition"
    HIERARCHY = "hierarchy"
    WORKFLOW = "workflow"
    TIMELINE = "timeline"
    COMMITTEE = "committee"
    POLICY = "policy"
    GOVERNANCE = "governance"
    COMPARISON = "comparison"
    RELATIONSHIP = "relationship"
    LIST = "list"
    TABLE = "table"
    LIFECYCLE = "lifecycle"
    DECISION_TREE = "decision_tree"
    RESPONSIBILITIES = "responsibilities"
    APPROVAL_FLOW = "approval_flow"
    ESCALATION = "escalation"
    METADATA_SCHEMA = "metadata_schema"
    TAXONOMY = "taxonomy"
    SECTION = "section"
    APPENDIX = "appendix"
    EXAMPLES = "examples"
    UNKNOWN = "unknown"


class EvidenceRelationKind(str, Enum):
    """Links between evidence nodes (structural only)."""

    PARENT_CHILD = "parent_child"
    SEQUENCE = "sequence"
    SAME_SECTION = "same_section"
    RELATED = "related"
