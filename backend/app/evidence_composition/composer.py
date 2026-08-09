"""Compose prioritized answer evidence from an Evidence Graph (Phase 4C)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.evidence_composition.enums import EvidencePriority
from app.evidence_composition.scoring import score_evidence_node
from app.evidence_composition.types import AnswerComposition, PrioritizedEvidence
from app.evidence_organization.types import EvidenceGraph

if TYPE_CHECKING:
    from app.answer_planning.types import AnswerPlan


def compose_answer_evidence(
    graph: EvidenceGraph | None,
    *,
    question: str,
    answer_plan: AnswerPlan | None = None,
) -> AnswerComposition:
    """Assign PRIMARY / SUPPORTING / OPTIONAL tiers to organized evidence nodes.

    Does not invent content, rewrite evidence, or change retrieval/organization.
    """
    answer_type = None
    if answer_plan is not None and getattr(answer_plan, "answer_type", None) is not None:
        answer_type = answer_plan.answer_type.value
    elif graph is not None:
        answer_type = graph.answer_type

    profile = graph.structure_profile if graph is not None else None
    if not graph or not graph.nodes:
        return AnswerComposition(
            decisions=["empty_evidence"],
            answer_type=answer_type,
            structure_profile=profile,
        )

    scored: list[PrioritizedEvidence] = []
    for node in graph.nodes:
        breakdown = score_evidence_node(
            node,
            question=question,
            answer_type=answer_type,
            structure_profile=profile,
        )
        scored.append(
            PrioritizedEvidence(
                node=node,
                priority=EvidencePriority.SUPPORTING,  # provisional
                score=breakdown.score,
                reasons=list(breakdown.reasons),
            )
        )

    scores = sorted((item.score for item in scored), reverse=True)
    top = scores[0] if scores else 0.0
    # Relative bands keep multi-document sets focused without hardcoding labels.
    primary_floor = max(0.45, top - 0.22)
    supporting_floor = max(0.28, primary_floor - 0.25)

    primary: list[PrioritizedEvidence] = []
    supporting: list[PrioritizedEvidence] = []
    optional: list[PrioritizedEvidence] = []
    decisions: list[str] = [
        f"answer_type={answer_type}",
        f"profile={profile}",
        f"top_score={top:.3f}",
        f"primary_floor={primary_floor:.3f}",
        f"supporting_floor={supporting_floor:.3f}",
    ]

    for item in scored:
        breakdown_optional = any(
            reason.startswith("optional_signal=") or reason == "appendix_structure"
            for reason in item.reasons
        )
        breakdown_primary = any(
            reason.startswith("primary_keywords=") for reason in item.reasons
        )

        if breakdown_optional and item.score < primary_floor:
            item.priority = EvidencePriority.OPTIONAL
            optional.append(item)
            continue

        if item.score >= primary_floor or (
            breakdown_primary and item.score >= supporting_floor
        ):
            item.priority = EvidencePriority.PRIMARY
            primary.append(item)
            continue

        if item.score >= supporting_floor:
            item.priority = EvidencePriority.SUPPORTING
            supporting.append(item)
            continue

        item.priority = EvidencePriority.OPTIONAL
        optional.append(item)

    # Guarantee at least one primary when evidence exists — promote top score.
    if not primary and scored:
        best = max(scored, key=lambda item: item.score)
        if best in supporting:
            supporting.remove(best)
        if best in optional:
            optional.remove(best)
        best.priority = EvidencePriority.PRIMARY
        best.reasons.append("promoted_top_score")
        primary.append(best)
        decisions.append(f"promoted_primary={best.node.label}")

    # Preserve organizer order within each tier so narrative sequence stays intact.
    order_index = {node.node_id: index for index, node in enumerate(graph.nodes)}
    primary.sort(key=lambda item: order_index.get(item.node.node_id, 10**9))
    supporting.sort(key=lambda item: order_index.get(item.node.node_id, 10**9))
    optional.sort(key=lambda item: order_index.get(item.node.node_id, 10**9))

    decisions.append(
        "final_composition="
        + f"primary={[p.node.label for p in primary]}; "
        + f"supporting={[p.node.label for p in supporting]}; "
        + f"optional={[p.node.label for p in optional]}"
    )

    return AnswerComposition(
        primary=primary,
        supporting=supporting,
        optional=optional,
        decisions=decisions,
        answer_type=answer_type,
        structure_profile=profile,
    )
