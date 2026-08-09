"""Evidence Organizer — regroup/reorder retrieved chunks into an Evidence Graph.

Never invents, summarizes, rewrites, or paraphrases. Every node cites chunk ids.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace
from typing import TYPE_CHECKING

from app.evidence_organization.enums import EvidenceRelationKind
from app.evidence_organization.ordering import (
    describe_ordering,
    matched_stage_name,
    stage_key_for_profile,
)
from app.evidence_organization.structure import detect_structure_kind, profile_for_answer_type
from app.evidence_organization.types import EvidenceGraph, EvidenceLink, EvidenceNode
from app.rag.types import RetrievalResult

if TYPE_CHECKING:
    from app.answer_planning.types import AnswerPlan

_HEADING_LINE_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*\.?\s+)?([A-Z][A-Za-z0-9 /,&'\-]{2,80})\s*$"
)


def _first_heading_label(content: str) -> str | None:
    for raw in (content or "").splitlines()[:6]:
        line = raw.strip()
        if not line or len(line) > 100:
            continue
        match = _HEADING_LINE_RE.match(line)
        if match:
            return match.group(1).strip()
        # Numbered section titles like "1.4 Mission"
        if re.match(r"^\d+(?:\.\d+)+\s+\S+", line):
            return re.sub(r"^\d+(?:\.\d+)+\s+", "", line).strip()[:80]
    return None


def _group_key(result: RetrievalResult) -> tuple[str, str, tuple[str, ...]]:
    """Stable group identity from retrieved metadata (fallback to heading/source)."""
    source = result.source or "unknown"
    if result.hierarchy_path:
        path = tuple(part.strip() for part in result.hierarchy_path if part and part.strip())
        if path:
            return source, "hierarchy", path
    title = (result.section_title or "").strip()
    if title:
        return source, "section", (title,)
    heading = _first_heading_label(result.content or "")
    if heading:
        return source, "heading", (heading,)
    page = result.page_number if result.page_number is not None else -1
    return source, "page", (f"page:{page}",)


def _label_from_key(key: tuple[str, str, tuple[str, ...]]) -> str:
    _source, kind, parts = key
    if not parts:
        return _source
    if kind == "hierarchy":
        return parts[-1]
    return parts[0]


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return (cleaned[:48] or "node")


def organize_evidence(
    results: list[RetrievalResult],
    *,
    answer_plan: AnswerPlan | None = None,
) -> EvidenceGraph:
    """Build an Evidence Graph from retrieved results only.

    Retrieval order/scores are not changed upstream; this function only
    reorganizes the provided list for prompting.
    """
    answer_type = (
        answer_plan.answer_type.value
        if answer_plan is not None and getattr(answer_plan, "answer_type", None) is not None
        else None
    )
    profile = profile_for_answer_type(answer_type)

    if not results:
        return EvidenceGraph(
            structure_profile=profile,
            answer_type=answer_type,
            ordering_decisions=["empty_retrieval"],
        )

    buckets: dict[tuple[str, str, tuple[str, ...]], list[tuple[int, RetrievalResult]]] = (
        defaultdict(list)
    )
    for rank, result in enumerate(results, start=1):
        buckets[_group_key(result)].append((rank, result))

    # Merge adjacent same-section chunks: already bucketed; sort each bucket by page/rank.
    provisional: list[EvidenceNode] = []
    for key, items in buckets.items():
        items_sorted = sorted(
            items,
            key=lambda pair: (
                pair[1].page_number if pair[1].page_number is not None else 10**9,
                pair[0],
            ),
        )
        label = _label_from_key(key)
        source = key[0]
        hierarchy = key[2] if key[1] == "hierarchy" else ()
        section_title = items_sorted[0][1].section_title
        chunk_ids = [item.chunk_id for _, item in items_sorted]
        pages = sorted(
            {
                item.page_number
                for _, item in items_sorted
                if item.page_number is not None
            }
        )
        texts = [(item.content or "").strip() for _, item in items_sorted if (item.content or "").strip()]
        ranks = [rank for rank, _ in items_sorted]
        combined_for_detect = "\n".join(texts[:2])
        structure = detect_structure_kind(
            label=label,
            section_title=section_title,
            hierarchy_path=hierarchy,
            chunk_type=items_sorted[0][1].chunk_type,
            content=combined_for_detect,
            answer_type=answer_type,
        )
        node_id = f"{_slug(source)}__{_slug(label)}"
        provisional.append(
            EvidenceNode(
                node_id=node_id,
                label=label,
                structure_kind=structure,
                chunk_ids=chunk_ids,
                source=source,
                page_numbers=pages,
                hierarchy_path=hierarchy,
                section_title=section_title,
                evidence_texts=texts,
                original_ranks=ranks,
            )
        )

    # Deduplicate node ids if collisions occur.
    seen_ids: dict[str, int] = {}
    unique_nodes: list[EvidenceNode] = []
    for node in provisional:
        count = seen_ids.get(node.node_id, 0)
        seen_ids[node.node_id] = count + 1
        if count:
            node = replace(node, node_id=f"{node.node_id}_{count + 1}")
        unique_nodes.append(node)

    # Order groups using profile-aware stage keys (only stages present in evidence).
    decorated: list[tuple[tuple, EvidenceNode, str | None]] = []
    for node in unique_nodes:
        min_page = min(node.page_numbers) if node.page_numbers else None
        min_rank = min(node.original_ranks) if node.original_ranks else 10**9
        key = stage_key_for_profile(
            profile=profile,
            label=node.label,
            hierarchy_path=node.hierarchy_path,
            evidence_texts=node.evidence_texts,
            page=min_page,
            original_rank=min_rank,
        )
        stage_name = None
        if profile in {"workflow", "definition", "governance", "approval_flow", "relationship"}:
            # key layout: (bucket, stage_index|page, ...)
            if isinstance(key[0], int) and key[0] == 0 and len(key) >= 2 and isinstance(key[1], int):
                stage_name = str(key[1])
        decorated.append((key, node, stage_name))

    decorated.sort(key=lambda item: item[0])
    ordered_nodes = [node for _, node, _ in decorated]

    # Parent-child links from hierarchy path prefixes when both ends exist.
    path_to_node = {
        node.hierarchy_path: node
        for node in ordered_nodes
        if node.hierarchy_path
    }
    links: list[EvidenceLink] = []
    for node in ordered_nodes:
        path = node.hierarchy_path
        if len(path) < 2:
            continue
        parent_path = path[:-1]
        parent = path_to_node.get(parent_path)
        if parent is None:
            continue
        if node.node_id not in parent.child_ids:
            parent.child_ids.append(node.node_id)
        links.append(
            EvidenceLink(
                from_node_id=parent.node_id,
                to_node_id=node.node_id,
                relation=EvidenceRelationKind.PARENT_CHILD,
                reason="hierarchy_path prefix present in retrieved metadata",
            )
        )

    # Sequence links in final ordered list (adjacent groups).
    applied_stages: list[str] = []
    for index, node in enumerate(ordered_nodes):
        stage_hit = matched_stage_name(profile, node.label)
        if stage_hit is None:
            stage_hit = matched_stage_name(
                profile, " ".join([node.label, *node.evidence_texts[:1]])
            )
        if stage_hit:
            applied_stages.append(f"{stage_hit}:{node.label}")

        if index + 1 < len(ordered_nodes):
            nxt = ordered_nodes[index + 1]
            links.append(
                EvidenceLink(
                    from_node_id=node.node_id,
                    to_node_id=nxt.node_id,
                    relation=EvidenceRelationKind.SEQUENCE,
                    reason=f"ordered by profile={profile}",
                )
            )

    decisions = describe_ordering(profile, applied_stages)
    decisions.append(f"groups={len(ordered_nodes)}")
    decisions.append(
        "chunk_mapping="
        + "; ".join(
            f"{node.label}<-{','.join(node.chunk_ids)}" for node in ordered_nodes
        )
    )

    return EvidenceGraph(
        nodes=ordered_nodes,
        links=links,
        ordering_decisions=decisions,
        structure_profile=profile,
        answer_type=answer_type,
    )
