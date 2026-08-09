"""Deterministic priority scoring for organized evidence nodes."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.evidence_organization.enums import EvidenceStructureKind
from app.evidence_organization.types import EvidenceNode

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")

# Always optional unless the question itself asks for them.
_OPTIONAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(history|historical|background)\b", re.I),
    re.compile(r"\b(headquarters|hq|geographic presence|branches?)\b", re.I),
    re.compile(r"\b(appendix|abbreviations?|acronyms?)\b", re.I),
    re.compile(r"\b(related documents?|references?|see also)\b", re.I),
    re.compile(r"\b(employee structure|job levels|titles by function)\b", re.I),
)

# Primary intent keywords by answer type / profile.
_PRIMARY_BY_TYPE: dict[str, tuple[str, ...]] = {
    "definition": (
        "mission",
        "vision",
        "core values",
        "values",
        "definition",
        "purpose",
        "meaning",
    ),
    "list_extraction": (
        "categor",
        "types",
        "list",
        "levels",
        "connections",
        "metadata",
        "taxonomy",
    ),
    "workflow": (
        "lifecycle",
        "creation",
        "draft",
        "approval",
        "publication",
        "retention",
        "archive",
        "version",
        "workflow",
        "journey",
        "process",
    ),
    "relationship": (
        "relationship",
        "identifier",
        "filename",
        "version",
        "naming",
        "hierarchy",
        "supports",
        "mapping",
    ),
    "governance": (
        "governance",
        "committee",
        "charter",
        "mandate",
        "oversight",
        "escalat",
    ),
    "decision_guidance": (
        "committee",
        "approv",
        "authority",
        "decision",
        "who should",
        "escalat",
    ),
    "policy_lookup": (
        "policy",
        "require",
        "scope",
        "exception",
        "retention",
        "must",
        "shall",
    ),
    "compliance": ("compliance", "obligation", "regulatory", "control"),
    "comparison": ("compar", "difference", "versus", "similar"),
    "explanation": ("how", "explain", "process", "component"),
    "summary": ("overview", "summary"),
    "reference_lookup": ("document id", "filename", "identifier", "where"),
    "troubleshooting": ("error", "issue", "cause", "fix"),
}

_STRUCTURE_AFFINITY: dict[str, tuple[EvidenceStructureKind, ...]] = {
    "definition": (EvidenceStructureKind.DEFINITION, EvidenceStructureKind.LIST),
    "list_extraction": (
        EvidenceStructureKind.LIST,
        EvidenceStructureKind.TABLE,
        EvidenceStructureKind.METADATA_SCHEMA,
        EvidenceStructureKind.TAXONOMY,
    ),
    "workflow": (
        EvidenceStructureKind.WORKFLOW,
        EvidenceStructureKind.LIFECYCLE,
        EvidenceStructureKind.APPROVAL_FLOW,
        EvidenceStructureKind.TIMELINE,
    ),
    "relationship": (
        EvidenceStructureKind.RELATIONSHIP,
        EvidenceStructureKind.HIERARCHY,
        EvidenceStructureKind.TAXONOMY,
    ),
    "governance": (
        EvidenceStructureKind.GOVERNANCE,
        EvidenceStructureKind.COMMITTEE,
        EvidenceStructureKind.ESCALATION,
    ),
    "decision_guidance": (
        EvidenceStructureKind.APPROVAL_FLOW,
        EvidenceStructureKind.COMMITTEE,
        EvidenceStructureKind.DECISION_TREE,
        EvidenceStructureKind.ESCALATION,
    ),
    "policy_lookup": (EvidenceStructureKind.POLICY,),
    "compliance": (EvidenceStructureKind.POLICY, EvidenceStructureKind.GOVERNANCE),
}

_SUPPORTING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(example|for example|e\.g\.)\b", re.I),
    re.compile(r"\b(responsib|raci|owner|accountable)\b", re.I),
    re.compile(r"\b(exception|note|notes|context)\b", re.I),
    re.compile(r"\b(naming|metadata)\b", re.I),
)


@dataclass(frozen=True)
class ScoreBreakdown:
    score: float
    reasons: tuple[str, ...]
    optional_signal: bool
    primary_signal: bool


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _node_haystack(node: EvidenceNode) -> str:
    return " ".join(
        [
            node.label,
            node.section_title or "",
            " ".join(node.hierarchy_path),
            " ".join(node.evidence_texts[:2]),
            node.source,
        ]
    )


def score_evidence_node(
    node: EvidenceNode,
    *,
    question: str,
    answer_type: str | None,
    structure_profile: str | None,
) -> ScoreBreakdown:
    """Score one organized evidence node for answer focus (0..1-ish)."""
    question_l = (question or "").lower()
    q_tokens = _tokens(question)
    haystack = _node_haystack(node)
    haystack_l = haystack.lower()
    label_l = (node.label or "").lower()
    reasons: list[str] = []
    score = 0.15  # base presence

    # Heading / label overlap with question tokens.
    label_tokens = _tokens(node.label + " " + (node.section_title or ""))
    overlap = label_tokens & q_tokens
    if overlap:
        boost = min(0.35, 0.12 * len(overlap))
        score += boost
        reasons.append(f"heading_overlap={sorted(overlap)[:4]}")

    # Broader lexical overlap with evidence text (light).
    body_tokens = _tokens(" ".join(node.evidence_texts[:1]))
    body_overlap = body_tokens & q_tokens
    if body_overlap:
        score += min(0.12, 0.03 * len(body_overlap))
        reasons.append("content_token_overlap")

    # Answer-type primary keyword hits.
    primary_keys = _PRIMARY_BY_TYPE.get(answer_type or "", ())
    primary_hits = [key for key in primary_keys if key in haystack_l or key in label_l]
    primary_signal = bool(primary_hits)
    if primary_hits:
        score += min(0.40, 0.14 * len(primary_hits))
        reasons.append(f"primary_keywords={primary_hits[:3]}")

    # Structure-kind affinity to answer type / profile.
    affinity_key = answer_type or structure_profile or ""
    affinity = _STRUCTURE_AFFINITY.get(affinity_key, ())
    if node.structure_kind in affinity:
        score += 0.18
        reasons.append(f"structure_affinity={node.structure_kind.value}")

    # Supporting signals — moderate boost, not primary.
    if any(pattern.search(haystack) for pattern in _SUPPORTING_PATTERNS):
        if not primary_signal:
            score += 0.08
            reasons.append("supporting_signal")

    # Chunk quality: prefer substantive prose over stubs.
    text_len = sum(len(t) for t in node.evidence_texts)
    if text_len >= 180:
        score += 0.10
        reasons.append("substantive_content")
    elif text_len < 40:
        score -= 0.12
        reasons.append("low_content_stub")

    # Document authority: source filename tokens overlapping question.
    source_tokens = _tokens(node.source.replace("_", " ").replace(".pdf", " "))
    source_overlap = source_tokens & q_tokens
    if source_overlap:
        score += 0.06
        reasons.append("source_name_overlap")

    # Optional demotion unless question asks for that topic.
    optional_signal = False
    for pattern in _OPTIONAL_PATTERNS:
        match = pattern.search(haystack)
        if not match:
            continue
        token = match.group(0).lower()
        # If the question explicitly asks for history/hq/etc., do not demote.
        if token in question_l or any(part in question_l for part in token.split()):
            continue
        optional_signal = True
        score -= 0.28
        reasons.append(f"optional_signal={token}")
        break

    # Appendix / examples structure kinds lean optional/supporting.
    if node.structure_kind == EvidenceStructureKind.APPENDIX:
        optional_signal = True
        score -= 0.20
        reasons.append("appendix_structure")
    elif node.structure_kind == EvidenceStructureKind.EXAMPLES and not primary_signal:
        score -= 0.05
        reasons.append("examples_structure")

    return ScoreBreakdown(
        score=round(max(0.0, min(1.25, score)), 4),
        reasons=tuple(reasons),
        optional_signal=optional_signal,
        primary_signal=primary_signal,
    )
