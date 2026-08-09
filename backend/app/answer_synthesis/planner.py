"""Deterministic synthesis planner (Phase 4F).

Consumes Answer Plan + Evidence Graph + Answer Composition.
Does not retrieve, rewrite chunk text, or call an LLM.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING

from app.answer_synthesis.ownership import (
    CONCEPT_FLOW,
    concept_flow_rank,
    detect_question_topics,
    infer_concept_label,
    source_matches_hints,
)
from app.answer_synthesis.types import SynthesisPlan, SynthesisSection
from app.answer_synthesis.unsupported import assess_unsupported_request

if TYPE_CHECKING:
    from app.answer_planning.types import AnswerPlan
    from app.evidence_composition.types import AnswerComposition, PrioritizedEvidence
    from app.evidence_organization.types import EvidenceGraph


_EXECUTIVE_RE = re.compile(
    r"\b("
    r"head of|you are the|500[- ]word|executive (?:brief|summary|report)|"
    r"enterprise knowledge management"
    r")\b",
    re.I,
)

_MULTI_DOC_SIGNAL_RE = re.compile(
    r"\b("
    r"journey|work together|standards work|end[- ]to[- ]end|create .+ policy|"
    r"governance journey|head of enterprise knowledge"
    r")\b",
    re.I,
)

_EXPECTED_CONCEPT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Mission", re.compile(r"\bmission\b", re.I)),
    ("Vision", re.compile(r"\bvision\b", re.I)),
    ("Core Values", re.compile(r"\b(core values?|values)\b", re.I)),
)


def _evidence_corpus(
    composition: AnswerComposition | None,
    graph: EvidenceGraph | None,
) -> str:
    parts: list[str] = []
    if composition is not None:
        for item in composition.all_items:
            parts.extend(item.node.evidence_texts)
            parts.append(item.node.source or "")
            parts.append(item.node.label or "")
    elif graph is not None:
        for node in graph.nodes:
            parts.extend(node.evidence_texts)
            parts.append(node.source or "")
            parts.append(node.label or "")
    return "\n".join(parts)


def _items_for_planning(
    composition: AnswerComposition | None,
    graph: EvidenceGraph | None,
) -> list:
    if composition is not None and composition.all_items:
        return list(composition.all_items)
    if graph is not None and graph.nodes:
        from app.evidence_composition.enums import EvidencePriority
        from app.evidence_composition.types import PrioritizedEvidence

        return [
            PrioritizedEvidence(
                node=node,
                priority=EvidencePriority.PRIMARY,
                score=1.0,
                reasons=["from_graph"],
            )
            for node in graph.nodes
        ]
    return []


def _select_primary_document(
    question: str,
    items: list,
) -> tuple[str | None, list[str]]:
    decisions: list[str] = []
    topics = detect_question_topics(question)
    sources_in_order: list[str] = []
    seen: set[str] = set()
    for item in items:
        source = item.node.source or ""
        if source and source not in seen:
            seen.add(source)
            sources_in_order.append(source)

    if not sources_in_order:
        return None, decisions

    for topic in topics:
        for source in sources_in_order:
            if source_matches_hints(source, topic.source_hints):
                decisions.append(f"primary_by_topic={topic.topic_key}:{source}")
                return source, decisions

    for item in items:
        priority = getattr(item.priority, "value", str(item.priority))
        if priority == "primary" and item.node.source:
            decisions.append(f"primary_by_composition={item.node.source}")
            return item.node.source, decisions

    decisions.append(f"primary_by_first_source={sources_in_order[0]}")
    return sources_in_order[0], decisions


def _group_sections(items: list, primary_document: str | None) -> list[SynthesisSection]:
    grouped: dict[str, SynthesisSection] = {}
    insertion_order: list[str] = []

    for item in items:
        node = item.node
        concept = infer_concept_label(
            node.label,
            node.source,
            list(node.evidence_texts),
        )
        priority = getattr(item.priority, "value", str(item.priority))
        if concept not in grouped:
            grouped[concept] = SynthesisSection(concept=concept)
            insertion_order.append(concept)
        section = grouped[concept]
        if node.source and node.source not in section.sources:
            section.sources.append(node.source)
        for text in node.evidence_texts:
            cleaned = (text or "").strip()
            if cleaned and cleaned not in section.evidence_texts:
                section.evidence_texts.append(cleaned)
                section.contribution_chars += len(cleaned)
        for chunk_id in node.chunk_ids:
            if chunk_id not in section.chunk_ids:
                section.chunk_ids.append(chunk_id)
        if primary_document and node.source == primary_document:
            section.owner_role = "primary"
        elif priority == "optional":
            if section.owner_role != "primary":
                section.owner_role = "context"
        elif section.owner_role != "primary":
            section.owner_role = "supporting"

    ranked = list(enumerate(insertion_order))
    ranked.sort(key=lambda pair: (concept_flow_rank(pair[1]), pair[0]))
    return [grouped[name] for _, name in ranked]


def _document_contribution(sections: list[SynthesisSection]) -> dict[str, float]:
    totals: dict[str, int] = defaultdict(int)
    for section in sections:
        if section.sources:
            share = section.contribution_chars // max(1, len(section.sources))
            for source in section.sources:
                totals[source] += share
        else:
            totals["(unknown)"] += section.contribution_chars
    grand = sum(totals.values()) or 1
    return {source: (chars / grand) * 100.0 for source, chars in totals.items()}


def _expected_concepts(question: str, answer_plan: AnswerPlan | None) -> list[str]:
    expected: list[str] = []
    q = question or ""
    for concept, pattern in _EXPECTED_CONCEPT_PATTERNS:
        if pattern.search(q) and concept not in expected:
            expected.append(concept)

    for concept in CONCEPT_FLOW:
        if re.search(rf"\b{re.escape(concept)}\b", q, re.I) and concept not in expected:
            expected.append(concept)

    if _MULTI_DOC_SIGNAL_RE.search(q):
        for concept in CONCEPT_FLOW:
            if concept not in expected:
                expected.append(concept)

    if answer_plan is not None and answer_plan.answer_type.value == "workflow":
        for concept in ("Naming", "Approval", "Retention", "Governance"):
            if concept not in expected:
                expected.append(concept)

    return expected


def plan_answer_synthesis(
    *,
    question: str,
    answer_plan: AnswerPlan | None = None,
    evidence_graph: EvidenceGraph | None = None,
    answer_composition: AnswerComposition | None = None,
) -> SynthesisPlan:
    """Build a concept-oriented synthesis plan for prompting."""
    plan = SynthesisPlan(
        answer_type=answer_plan.answer_type.value if answer_plan is not None else None,
    )
    corpus = _evidence_corpus(answer_composition, evidence_graph)
    unsupported = assess_unsupported_request(question=question, evidence_text=corpus)
    if unsupported.is_unsupported:
        plan.is_unsupported = True
        plan.mode = "unsupported"
        plan.refusal_message = unsupported.refusal_message
        plan.unsupported_concepts = list(unsupported.unsupported_concepts)
        plan.decisions.extend(unsupported.reasons)
        plan.decisions.append("mode=unsupported")
        return plan

    items = _items_for_planning(answer_composition, evidence_graph)
    if not items:
        plan.mode = "single_document"
        plan.decisions.append("empty_evidence")
        return plan

    primary, primary_decisions = _select_primary_document(question, items)
    plan.primary_document = primary
    plan.decisions.extend(primary_decisions)

    sections = [
        section for section in _group_sections(items, primary) if section.evidence_texts
    ]
    plan.sections = sections
    plan.concept_flow = [section.concept for section in sections]
    plan.concept_coverage = list(plan.concept_flow)
    plan.document_contribution = _document_contribution(sections)

    supporting: list[str] = []
    context: list[str] = []
    seen_docs: set[str] = set()
    for section in sections:
        for source in section.sources:
            if not source or source == primary or source in seen_docs:
                continue
            seen_docs.add(source)
            if section.owner_role == "context":
                context.append(source)
            else:
                supporting.append(source)
    plan.supporting_documents = supporting
    plan.context_documents = context

    expected = _expected_concepts(question, answer_plan)
    covered = {section.concept for section in sections}
    plan.dropped_concepts = [concept for concept in expected if concept not in covered]

    unique_sources = {source for section in sections for source in section.sources}
    if _EXECUTIVE_RE.search(question or ""):
        plan.mode = "executive"
    elif len(unique_sources) >= 2 or (
        answer_plan is not None
        and answer_plan.answer_type.value in {"workflow", "relationship"}
    ):
        plan.mode = "multi_document"
    else:
        plan.mode = "single_document"

    plan.decisions.append(f"mode={plan.mode}")
    plan.decisions.append(f"sections={len(sections)}")
    plan.decisions.append(f"sources={len(unique_sources)}")
    if plan.dropped_concepts:
        plan.decisions.append(f"dropped_concepts={plan.dropped_concepts}")

    return plan
