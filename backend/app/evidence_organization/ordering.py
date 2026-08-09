"""Deterministic ordering of evidence groups from retrieved signals only."""

from __future__ import annotations

import re
from typing import Iterable

# Workflow / document-lifecycle stages. A group is placed only if its own
# label/content matches; missing stages are never invented.
_WORKFLOW_STAGES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("creation", re.compile(r"\b(creat|draft|authoring|originate)", re.I)),
    ("metadata", re.compile(r"\bmetadata\b", re.I)),
    ("classification", re.compile(r"\b(classif|taxonomy|categor)", re.I)),
    ("naming", re.compile(r"\b(naming|filename|document id|identifier)", re.I)),
    ("review", re.compile(r"\b(peer review|review)\b", re.I)),
    ("approval", re.compile(r"\bapprov", re.I)),
    ("publication", re.compile(r"\b(publish|publication|release)\b", re.I)),
    ("retention", re.compile(r"\b(retention|retain)", re.I)),
    ("archive", re.compile(r"\b(archive|archival|disposal|destruction)", re.I)),
)

_DEFINITION_STAGES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("mission", re.compile(r"\bmission\b", re.I)),
    ("vision", re.compile(r"\bvision\b", re.I)),
    ("core_values", re.compile(r"\bcore values?\b", re.I)),
    ("culture", re.compile(r"\b(culture|behaviour|behavior)\b", re.I)),
)

_GOVERNANCE_STAGES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("committee", re.compile(r"\b(committee|charter|board)\b", re.I)),
    ("authority", re.compile(r"\b(authority|mandate|delegat)", re.I)),
    ("responsibilities", re.compile(r"\b(responsib|raci|duties)", re.I)),
    ("escalation", re.compile(r"\bescalat", re.I)),
    ("interactions", re.compile(r"\b(interact|coordination|handoff)", re.I)),
    ("supporting_documents", re.compile(r"\b(related documents?|supporting|references?)\b", re.I)),
)

_RELATIONSHIP_STAGES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("concept_a", re.compile(r"\b(identifier|document id|filename|naming)\b", re.I)),
    ("concept_b", re.compile(r"\b(version|versioning)\b", re.I)),
    ("relationship", re.compile(r"\b(relationship|work together|mapping|linked)\b", re.I)),
    ("business_meaning", re.compile(r"\b(purpose|business|significance|impact)\b", re.I)),
)


def _match_stage(
    stages: tuple[tuple[str, re.Pattern[str]], ...],
    text: str,
) -> tuple[int, str] | None:
    for index, (name, pattern) in enumerate(stages):
        if pattern.search(text):
            return index, name
    return None


def _haystack(label: str, texts: Iterable[str], hierarchy: tuple[str, ...]) -> str:
    return " ".join(
        [
            label,
            " ".join(hierarchy),
            " ".join(texts),
        ]
    )


def _stage_hit_for_profile(profile: str, label: str, hierarchy_path: tuple[str, ...], evidence_texts: list[str]):
    """Prefer label/hierarchy matches; fall back to evidence body only if needed."""
    label_text = _haystack(label, (), hierarchy_path)
    body_text = _haystack(label, evidence_texts[:2], hierarchy_path)
    if profile == "workflow":
        return _match_stage(_WORKFLOW_STAGES, label_text) or _match_stage(
            _WORKFLOW_STAGES, body_text
        )
    if profile == "definition":
        return _match_stage(_DEFINITION_STAGES, label_text) or _match_stage(
            _DEFINITION_STAGES, body_text
        )
    if profile in {"governance", "approval_flow"}:
        return _match_stage(_GOVERNANCE_STAGES, label_text) or _match_stage(
            _GOVERNANCE_STAGES, body_text
        )
    if profile == "relationship":
        return _match_stage(_RELATIONSHIP_STAGES, label_text) or _match_stage(
            _RELATIONSHIP_STAGES, body_text
        )
    return None


def stage_key_for_profile(
    *,
    profile: str,
    label: str,
    hierarchy_path: tuple[str, ...],
    evidence_texts: list[str],
    page: int | None,
    original_rank: int,
) -> tuple:
    """Return a sort key. Unmatched groups keep stable page/rank order at the end."""
    page_key = page if page is not None else 10**9
    hit = _stage_hit_for_profile(profile, label, hierarchy_path, evidence_texts)
    if hit and profile in {
        "workflow",
        "definition",
        "governance",
        "approval_flow",
        "relationship",
    }:
        return (0, hit[0], page_key, original_rank, label)
    if profile in {
        "workflow",
        "definition",
        "governance",
        "approval_flow",
        "relationship",
    }:
        return (1, page_key, original_rank, label)

    # list / section / policy / comparison — stable document order
    return (0, page_key, original_rank, label)


def matched_stage_name(profile: str, text: str) -> str | None:
    """Return the first matching stage name for diagnostics, if any."""
    hit = _stage_hit_for_profile(profile, text, (), [])
    if hit:
        return hit[1]
    # Fallback: treat full text as body when caller passes combined haystack.
    if profile == "workflow":
        hit = _match_stage(_WORKFLOW_STAGES, text)
    elif profile == "definition":
        hit = _match_stage(_DEFINITION_STAGES, text)
    elif profile in {"governance", "approval_flow"}:
        hit = _match_stage(_GOVERNANCE_STAGES, text)
    elif profile == "relationship":
        hit = _match_stage(_RELATIONSHIP_STAGES, text)
    else:
        return None
    return hit[1] if hit else None


def describe_ordering(profile: str, applied_stages: list[str]) -> list[str]:
    """Human-readable ordering decisions for diagnostics."""
    decisions = [f"profile={profile}"]
    if applied_stages:
        decisions.append("stage_order=" + " -> ".join(applied_stages))
    else:
        decisions.append("stage_order=document_reading_order")
    return decisions
