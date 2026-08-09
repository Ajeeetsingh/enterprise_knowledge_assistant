"""Detect enterprise structure kinds from retrieved evidence signals only."""

from __future__ import annotations

import re

from app.evidence_organization.enums import EvidenceStructureKind

# Label/content keyword → structure. Matched against retrieved text/metadata only.
_STRUCTURE_PATTERNS: tuple[tuple[EvidenceStructureKind, re.Pattern[str]], ...] = (
    (EvidenceStructureKind.TAXONOMY, re.compile(r"\b(taxonomy|hierarchy|level\s*[1-4]|l[1-4]\b)", re.I)),
    (EvidenceStructureKind.METADATA_SCHEMA, re.compile(r"\b(metadata (?:categor|schema|field|standard)|administrative metadata|business metadata)", re.I)),
    (EvidenceStructureKind.APPROVAL_FLOW, re.compile(r"\b(approval (?:flow|path|authority|matrix)|who (?:approves|must approve)|delegated authority)", re.I)),
    (EvidenceStructureKind.ESCALATION, re.compile(r"\b(escalat)", re.I)),
    (EvidenceStructureKind.COMMITTEE, re.compile(r"\b(committee|charter|board)\b", re.I)),
    (EvidenceStructureKind.LIFECYCLE, re.compile(r"\b(lifecycle|life cycle|retention|archive|publication)", re.I)),
    (EvidenceStructureKind.WORKFLOW, re.compile(r"\b(workflow|process flow|journey|step[- ]by[- ]step)", re.I)),
    (EvidenceStructureKind.TIMELINE, re.compile(r"\b(timeline|chronolog|effective date|milestone)", re.I)),
    (EvidenceStructureKind.POLICY, re.compile(r"\b(policy|procedure|standard)\b", re.I)),
    (EvidenceStructureKind.GOVERNANCE, re.compile(r"\b(governance|oversight|mandate)\b", re.I)),
    (EvidenceStructureKind.RESPONSIBILITIES, re.compile(r"\b(responsib|raci|accountable|owner)\b", re.I)),
    (EvidenceStructureKind.DECISION_TREE, re.compile(r"\b(decision tree|if .+ then|decision path)\b", re.I)),
    (EvidenceStructureKind.COMPARISON, re.compile(r"\b(compar|versus|vs\.?|difference)\b", re.I)),
    (EvidenceStructureKind.RELATIONSHIP, re.compile(r"\b(relationship|work together|mapping|related to)\b", re.I)),
    (EvidenceStructureKind.APPENDIX, re.compile(r"\b(appendix)\b", re.I)),
    (EvidenceStructureKind.EXAMPLES, re.compile(r"\b(example|for example|e\.g\.)\b", re.I)),
    (EvidenceStructureKind.DEFINITION, re.compile(r"\b(mission|vision|definition|what is|means)\b", re.I)),
    (EvidenceStructureKind.LIST, re.compile(r"\b(categories|types of|includes?:|core values)\b", re.I)),
)


def detect_structure_kind(
    *,
    label: str,
    section_title: str | None,
    hierarchy_path: tuple[str, ...],
    chunk_type: str | None,
    content: str,
    answer_type: str | None = None,
) -> EvidenceStructureKind:
    """Infer structure kind from retrieved metadata/content (never invents nodes)."""
    if chunk_type == "table":
        return EvidenceStructureKind.TABLE
    if chunk_type == "list":
        return EvidenceStructureKind.LIST

    haystack = " ".join(
        part
        for part in (
            label,
            section_title or "",
            " ".join(hierarchy_path),
            content[:800],
        )
        if part
    )
    for kind, pattern in _STRUCTURE_PATTERNS:
        if pattern.search(haystack):
            return kind

    # Soft bias from answer plan type when local signals are weak.
    if answer_type == "workflow":
        return EvidenceStructureKind.WORKFLOW
    if answer_type == "relationship":
        return EvidenceStructureKind.RELATIONSHIP
    if answer_type == "list_extraction":
        return EvidenceStructureKind.LIST
    if answer_type == "governance":
        return EvidenceStructureKind.GOVERNANCE
    if answer_type == "decision_guidance":
        return EvidenceStructureKind.APPROVAL_FLOW
    if answer_type == "definition":
        return EvidenceStructureKind.DEFINITION
    if answer_type == "comparison":
        return EvidenceStructureKind.COMPARISON
    if answer_type == "policy_lookup":
        return EvidenceStructureKind.POLICY

    if hierarchy_path and len(hierarchy_path) >= 2:
        return EvidenceStructureKind.HIERARCHY
    return EvidenceStructureKind.SECTION


def profile_for_answer_type(answer_type: str | None) -> str:
    """High-level organization profile name for diagnostics/prompt."""
    mapping = {
        "definition": "definition",
        "explanation": "section",
        "relationship": "relationship",
        "comparison": "comparison",
        "workflow": "workflow",
        "policy_lookup": "policy",
        "governance": "governance",
        "decision_guidance": "approval_flow",
        "troubleshooting": "section",
        "summary": "section",
        "compliance": "policy",
        "list_extraction": "list",
        "reference_lookup": "section",
    }
    return mapping.get(answer_type or "", "section")
