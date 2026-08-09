"""Individual deterministic GAQA checks."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.gaqa.concepts import contains_concept, extract_question_concepts, tokenize
from app.gaqa.types import (
    BlueprintSectionItem,
    ClaimSupportItem,
    ConceptCoverageItem,
    EvidenceMappingItem,
)

if TYPE_CHECKING:
    from app.answer_planning.types import AnswerPlan
    from app.evidence_composition.types import AnswerComposition
    from app.evidence_organization.types import EvidenceGraph

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD_RE = re.compile(r"[a-z0-9]{3,}", re.I)

# Blueprint section → search cues in the answer (not requiring exact headings).
_SECTION_CUES: dict[str, tuple[str, ...]] = {
    "Short definition": ("is ", "means", "defined as", "mission", "vision", "refers to"),
    "Purpose": ("purpose", "intended", "aims", "designed to"),
    "Key characteristics": ("key", "include", "characteristics", "consists"),
    "Important notes": ("note", "important", "exception", "must"),
    "Overview": ("overview", "overall", "in summary", "broadly"),
    "How it works": ("how", "works by", "process", "through"),
    "Key components": ("component", "element", "includes", "consists"),
    "Practical implications": ("implication", "means that", "therefore", "impact"),
    "Introduce the concepts": ("concept", "includes", "involves", "refers"),
    "Explain each concept": ("is ", "are ", "defined", "means"),
    "Explain how they relate": ("together", "relate", "relationship", "connect", "supports"),
    "Business significance": ("business", "enterprise", "significance", "important", "enables"),
    "Entities being compared": ("compared", "versus", "vs", "between"),
    "Key differences": ("difference", "differ", "unlike", "whereas"),
    "Key similarities": ("similar", "both", "shared", "alike"),
    "When each applies": ("when", "applies", "use", "appropriate"),
    "Objective": ("objective", "goal", "purpose", "aims"),
    "Ordered steps": ("step", "first", "then", "next", "finally", "stage"),
    "Roles and responsibilities": ("role", "responsible", "owner", "accountable"),
    "Outcome": ("outcome", "result", "produces", "ensures"),
    "Scope": ("scope", "applies to", "covers", "in scope"),
    "Requirements": ("require", "must", "shall", "obligation"),
    "Exceptions": ("exception", "unless", "exclude"),
    "Governance": ("governance", "oversight", "committee", "authority"),
    "Governance context": ("governance", "context", "framework"),
    "Bodies and roles": ("committee", "body", "role", "board"),
    "Authorities and mandates": ("authority", "mandate", "delegat"),
    "Escalation or oversight": ("escalat", "oversight"),
    "Decision to be made": ("decision", "approve", "which"),
    "Applicable criteria": ("criteria", "when", "threshold", "limit"),
    "Recommended authority or path": ("committee", "authority", "should", "approv"),
    "Constraints and notes": ("constraint", "note", "limit", "except"),
    "Direct answer list": ("1.", "2.", "-", "include", "are"),
    "Brief description of each item": ("is ", "are ", "includes", "covers"),
    "Source context notes": ("document", "standard", "according", "defined"),
    "Direct reference answer": ("is ", "id", "format", "named"),
    "Where it appears": ("section", "page", "document", "appears"),
    "Related identifiers or pointers": ("id", "code", "reference", "filename"),
    "High-level summary": ("summary", "overall", "in brief"),
    "Key points": ("key", "main", "include"),
    "Supporting details": ("detail", "also", "additionally"),
    "Problem summary": ("problem", "issue", "error"),
    "Likely causes from the evidence": ("cause", "because", "due to"),
    "Recommended checks or actions": ("check", "action", "should", "verify"),
    "Escalation or follow-up": ("escalat", "follow"),
    "Obligation or requirement": ("must", "require", "obligation"),
    "Who it applies to": ("applies", "employees", "applies to"),
    "Controls or evidence expected": ("control", "evidence", "retain"),
    "Consequences or related governance": ("consequence", "governance", "penalty"),
}


_WORKFLOW_ORDER = (
    "creation",
    "metadata",
    "classification",
    "naming",
    "review",
    "approval",
    "publication",
    "retention",
    "archive",
)


def check_question_coverage(
    question: str,
    answer: str,
    evidence_text: str,
) -> tuple[list[ConceptCoverageItem], list[str]]:
    concepts = extract_question_concepts(question)
    items: list[ConceptCoverageItem] = []
    missing: list[str] = []
    for concept in concepts:
        in_answer = contains_concept(answer, concept)
        in_evidence = contains_concept(evidence_text, concept)
        items.append(
            ConceptCoverageItem(
                concept=concept,
                present_in_answer=in_answer,
                present_in_evidence=in_evidence,
            )
        )
        if not in_answer:
            missing.append(concept)
    return items, missing


def check_blueprint_compliance(
    answer: str,
    answer_plan: AnswerPlan | None,
) -> tuple[list[BlueprintSectionItem], float]:
    if answer_plan is None:
        return [], 1.0
    lowered = (answer or "").lower()
    items: list[BlueprintSectionItem] = []
    for section in answer_plan.blueprint.sections:
        cues = _SECTION_CUES.get(section, tuple(section.lower().split()[:3]))
        present = any(cue.lower() in lowered for cue in cues)
        # Also accept presence of distinctive section words.
        if not present:
            tokens = [t for t in section.lower().split() if len(t) > 3]
            present = bool(tokens) and sum(1 for t in tokens if t in lowered) >= max(
                1, len(tokens) // 2
            )
        items.append(BlueprintSectionItem(section=section, present=present))
    if not items:
        return items, 1.0
    compliance = sum(1 for item in items if item.present) / len(items)
    return items, compliance


def check_evidence_mapping(
    answer: str,
    composition: AnswerComposition | None,
    graph: EvidenceGraph | None,
) -> list[EvidenceMappingItem]:
    nodes = []
    if composition is not None:
        nodes = [item.node for item in composition.primary + composition.supporting]
    elif graph is not None:
        nodes = list(graph.nodes)

    mappings: list[EvidenceMappingItem] = []
    answer_l = (answer or "").lower()
    for node in nodes:
        label_l = (node.label or "").lower()
        label_tokens = [t for t in re.findall(r"[a-z0-9]{3,}", label_l)]
        mentioned = bool(label_tokens) and any(tok in answer_l for tok in label_tokens[:3])
        evidence_blob = " ".join(node.evidence_texts).lower()
        evidence_tokens = tokenize(evidence_blob)
        answer_tokens = tokenize(answer)
        overlap = evidence_tokens & answer_tokens
        if not evidence_tokens:
            support = "unsupported"
        else:
            ratio = len(overlap) / max(1, min(40, len(evidence_tokens)))
            if mentioned and ratio >= 0.08:
                support = "supported"
            elif mentioned or ratio >= 0.05:
                support = "partially_supported"
            else:
                support = "unsupported"
        mappings.append(
            EvidenceMappingItem(
                label=node.label,
                source=node.source,
                chunk_ids=tuple(node.chunk_ids),
                mentioned_in_answer=mentioned,
                support=support,
            )
        )
    return mappings


def check_unsupported_claims(
    answer: str,
    evidence_text: str,
) -> tuple[list[ClaimSupportItem], int]:
    evidence_tokens = tokenize(evidence_text)
    sentences = [
        part.strip()
        for part in _SENTENCE_SPLIT_RE.split(answer or "")
        if part and len(part.strip()) >= 25
    ]
    # Cap for latency — validate the most contentful sentences first.
    sentences = sorted(sentences, key=len, reverse=True)[:12]
    items: list[ClaimSupportItem] = []
    unsupported = 0
    for sentence in sentences:
        tokens = tokenize(sentence)
        if len(tokens) < 4:
            continue
        overlap = tokens & evidence_tokens
        ratio = len(overlap) / max(1, len(tokens))
        if ratio >= 0.28:
            support = "supported"
        elif ratio >= 0.12:
            support = "partially_supported"
        else:
            support = "unsupported"
            unsupported += 1
        items.append(
            ClaimSupportItem(
                excerpt=sentence[:220],
                support=support,
                overlap_ratio=ratio,
            )
        )
    return items, unsupported


def check_redundancy(answer: str, concepts: list[str]) -> list[str]:
    lowered = (answer or "").lower()
    redundant: list[str] = []
    for concept in concepts:
        # Count case-insensitive occurrences of the primary alias.
        alias = concept.lower()
        count = lowered.count(alias)
        if count >= 3:
            redundant.append(f"{concept}×{count}")
    # Generic repeated 5-gram detection (lightweight).
    words = _WORD_RE.findall(lowered)
    if len(words) >= 12:
        seen: dict[str, int] = {}
        for index in range(len(words) - 4):
            gram = " ".join(words[index : index + 5])
            seen[gram] = seen.get(gram, 0) + 1
        for gram, count in seen.items():
            if count >= 3 and gram not in redundant:
                redundant.append(f"phrase×{count}:{gram}")
                if len(redundant) >= 5:
                    break
    return redundant


def check_ordering(
    answer: str,
    answer_plan: AnswerPlan | None,
) -> tuple[bool, list[str]]:
    notes: list[str] = []
    if answer_plan is None:
        return True, notes
    answer_type = answer_plan.answer_type.value
    lowered = (answer or "").lower()

    if answer_type in {"workflow", "governance"}:
        positions: list[tuple[int, str]] = []
        for stage in _WORKFLOW_ORDER:
            pos = lowered.find(stage)
            if pos >= 0:
                positions.append((pos, stage))
        if len(positions) >= 2:
            ordered = sorted(positions, key=lambda item: item[0])
            names = [name for _, name in ordered]
            expected = [name for name in _WORKFLOW_ORDER if name in names]
            if names != expected:
                notes.append(
                    f"workflow_stage_order_observed={names}; expected_relative={expected}"
                )
                return False, notes
        return True, notes

    # Blueprint section cue order for definition-like answers with mission/vision/values.
    if answer_type == "definition":
        markers = [("mission", "Mission"), ("vision", "Vision"), ("core values", "Core Values")]
        positions = []
        for marker, label in markers:
            pos = lowered.find(marker)
            if pos >= 0:
                positions.append((pos, label))
        if len(positions) >= 2:
            ordered_labels = [label for _, label in sorted(positions, key=lambda item: item[0])]
            expected = [label for _, label in markers if label in ordered_labels]
            if ordered_labels != expected:
                notes.append(
                    f"definition_order_observed={ordered_labels}; expected={expected}"
                )
                return False, notes
    return True, notes
