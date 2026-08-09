"""Unit tests for Phase 4B evidence organization."""

from __future__ import annotations

from app.answer_planning import plan_answer
from app.evidence_organization import organize_evidence
from app.evidence_organization.enums import EvidenceRelationKind, EvidenceStructureKind
from app.llm.prompt_builder import PromptBuilder
from app.rag.types import RetrievalResult


def _chunk(
    chunk_id: str,
    content: str,
    *,
    source: str = "COMPANY_PROFILE.pdf",
    page: int | None = 10,
    section_title: str | None = None,
    hierarchy_path: tuple[str, ...] | None = None,
    chunk_type: str | None = "subsection",
    rank: int = 1,
) -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source=source,
        category="general",
        confidence=0.8,
        chunk_id=chunk_id,
        page_number=page,
        section_title=section_title,
        hierarchy_path=hierarchy_path,
        chunk_type=chunk_type,
        final_rank=rank,
    )


def test_groups_mission_vision_values_and_orders_definition_profile() -> None:
    results = [
        _chunk(
            "c-values",
            "1.6 Core Values\nIntegrity First\nClient Stewardship",
            section_title="1.6 Core Values",
            hierarchy_path=("1 Company Overview", "1.6 Core Values"),
            page=10,
            rank=1,
        ),
        _chunk(
            "c-behaviors",
            "Employee Behaviors\nObservable conduct linked to values",
            section_title="Employee Behaviors",
            hierarchy_path=("1 Company Overview", "Employee Behaviors"),
            page=11,
            rank=2,
        ),
        _chunk(
            "c-mission",
            "1.4 Mission\nTo steward our clients' financial lives with precision.",
            section_title="1.4 Mission",
            hierarchy_path=("1 Company Overview", "1.4 Mission"),
            page=10,
            rank=3,
        ),
        _chunk(
            "c-vision",
            "1.5 Vision\nTo be the most trusted and operationally resilient bank.",
            section_title="1.5 Vision",
            hierarchy_path=("1 Company Overview", "1.5 Vision"),
            page=10,
            rank=4,
        ),
    ]
    plan = plan_answer("What is Apex National Bank's mission, vision, and core values?")
    graph = organize_evidence(results, answer_plan=plan)

    labels = [node.label for node in graph.nodes]
    assert "1.4 Mission" in labels or "Mission" in " ".join(labels)
    # Mission before Vision before Core Values when signals present.
    mission_idx = next(i for i, n in enumerate(graph.nodes) if "Mission" in n.label)
    vision_idx = next(i for i, n in enumerate(graph.nodes) if "Vision" in n.label)
    values_idx = next(i for i, n in enumerate(graph.nodes) if "Core Values" in n.label)
    assert mission_idx < vision_idx < values_idx

    all_chunk_ids = {cid for node in graph.nodes for cid in node.chunk_ids}
    assert all_chunk_ids == {"c-values", "c-behaviors", "c-mission", "c-vision"}
    # No invented content — exact texts preserved.
    mission_node = next(n for n in graph.nodes if "Mission" in n.label)
    assert "To steward our clients' financial lives" in mission_node.evidence_texts[0]


def test_merges_same_section_chunks_without_rewriting() -> None:
    results = [
        _chunk(
            "a1",
            "Integrity First — regulated obligation precedes commercial opportunity.",
            section_title="1.6 Core Values",
            hierarchy_path=("1 Company Overview", "1.6 Core Values"),
            page=10,
            rank=1,
        ),
        _chunk(
            "a2",
            "Client Stewardship — client interest over the full relationship life.",
            section_title="1.6 Core Values",
            hierarchy_path=("1 Company Overview", "1.6 Core Values"),
            page=10,
            rank=2,
        ),
    ]
    graph = organize_evidence(results, answer_plan=plan_answer("What are the core values?"))
    assert len(graph.nodes) == 1
    assert graph.nodes[0].chunk_ids == ["a1", "a2"]
    assert len(graph.nodes[0].evidence_texts) == 2
    assert graph.nodes[0].evidence_texts[0].startswith("Integrity First")


def test_workflow_orders_only_stages_present_in_evidence() -> None:
    results = [
        _chunk(
            "ret",
            "Retention schedules define how long records are kept.",
            source="005_RECORDS_RETENTION_POLICY.pdf",
            section_title="Retention",
            page=12,
            rank=1,
        ),
        _chunk(
            "create",
            "Document creation begins with drafting under the owning function.",
            source="004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf",
            section_title="Creation",
            page=3,
            rank=2,
        ),
        _chunk(
            "approve",
            "Approval is required before publication.",
            source="006_APPROVAL_AUTHORITY_MATRIX.pdf",
            section_title="Approval",
            page=5,
            rank=3,
        ),
        # Unrelated noise — remains, but after matched stages when profile applies.
        _chunk(
            "noise",
            "Geographic presence overview for branches.",
            source="COMPANY_PROFILE.pdf",
            section_title="Geographic Presence",
            page=20,
            rank=4,
        ),
    ]
    plan = plan_answer("Describe the complete governance journey.")
    graph = organize_evidence(results, answer_plan=plan)
    labels = [n.label for n in graph.nodes]
    create_i = labels.index("Creation")
    approve_i = labels.index("Approval")
    retain_i = labels.index("Retention")
    assert create_i < approve_i < retain_i
    assert any(link.relation == EvidenceRelationKind.SEQUENCE for link in graph.links)


def test_parent_child_links_from_hierarchy_path() -> None:
    results = [
        _chunk(
            "parent",
            "1 Company Overview",
            section_title="1 Company Overview",
            hierarchy_path=("1 Company Overview",),
            page=6,
        ),
        _chunk(
            "child",
            "1.4 Mission body text",
            section_title="1.4 Mission",
            hierarchy_path=("1 Company Overview", "1.4 Mission"),
            page=10,
        ),
    ]
    graph = organize_evidence(results)
    assert any(
        link.relation == EvidenceRelationKind.PARENT_CHILD for link in graph.links
    )
    parent = next(n for n in graph.nodes if n.label == "1 Company Overview")
    child = next(n for n in graph.nodes if "Mission" in n.label)
    assert child.node_id in parent.child_ids


def test_does_not_invent_missing_workflow_stages() -> None:
    results = [
        _chunk(
            "only-approval",
            "Approval Authority Matrix rows for spend limits.",
            source="006_APPROVAL_AUTHORITY_MATRIX.pdf",
            section_title="Approval Authority",
            page=4,
        ),
    ]
    plan = plan_answer("Describe the complete governance journey.")
    graph = organize_evidence(results, answer_plan=plan)
    labels = [n.label.lower() for n in graph.nodes]
    assert "creation" not in labels
    assert "archive" not in labels
    assert len(graph.nodes) == 1


def test_prompt_builder_uses_evidence_graph_instead_of_flat_list() -> None:
    results = [
        _chunk(
            "m1",
            "1.4 Mission\nTo steward clients.",
            section_title="1.4 Mission",
            hierarchy_path=("Overview", "1.4 Mission"),
        ),
        _chunk(
            "v1",
            "1.5 Vision\nMost trusted bank.",
            section_title="1.5 Vision",
            hierarchy_path=("Overview", "1.5 Vision"),
        ),
    ]
    plan = plan_answer("What is Apex National Bank's mission, vision, and core values?")
    graph = organize_evidence(results, answer_plan=plan)
    prompt = PromptBuilder().build(
        "What is Apex National Bank's mission, vision, and core values?",
        results,
        answer_plan=plan,
        evidence_graph=graph,
    )
    assert "Organized evidence graph" in prompt.user
    assert "chunk_ids:" in prompt.user
    assert "To steward clients." in prompt.user
    assert "[Excerpt 1]" not in prompt.user
    assert "Definition_v1" in prompt.user


def test_retrieval_chunk_set_unchanged() -> None:
    """Organization must not drop or fabricate chunk ids."""
    results = [
        _chunk("x1", "Mission text", section_title="Mission", page=1, rank=1),
        _chunk("x2", "Vision text", section_title="Vision", page=2, rank=2),
        _chunk(
            "x3",
            "Table of metadata categories",
            source="002_ENTERPRISE_METADATA_STANDARD.pdf",
            section_title="Metadata Categories",
            chunk_type="table",
            page=8,
            rank=3,
        ),
    ]
    graph = organize_evidence(
        results,
        answer_plan=plan_answer(
            "What are the different categories of metadata defined by the Enterprise Metadata Standard?"
        ),
    )
    assert {c for n in graph.nodes for c in n.chunk_ids} == {"x1", "x2", "x3"}
    assert any(n.structure_kind == EvidenceStructureKind.TABLE for n in graph.nodes)
