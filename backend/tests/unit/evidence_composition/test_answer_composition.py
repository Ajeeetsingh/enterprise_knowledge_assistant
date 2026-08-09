"""Unit tests for Phase 4C evidence prioritization."""

from __future__ import annotations

from app.answer_planning import plan_answer
from app.evidence_composition import EvidencePriority, compose_answer_evidence
from app.evidence_organization import organize_evidence
from app.llm.prompt_builder import PromptBuilder
from app.rag.types import RetrievalResult


def _chunk(
    chunk_id: str,
    content: str,
    *,
    source: str = "COMPANY_PROFILE.pdf",
    page: int = 10,
    section: str,
    hierarchy: tuple[str, ...] | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source=source,
        category="general",
        confidence=0.8,
        chunk_id=chunk_id,
        page_number=page,
        section_title=section,
        hierarchy_path=hierarchy or (section,),
        chunk_type="subsection",
    )


def test_mission_vision_values_are_primary_history_optional() -> None:
    question = "What is Apex National Bank's mission, vision, and core values?"
    results = [
        _chunk(
            "hist",
            "1.3 History\nFounded decades ago in multiple markets.",
            section="1.3 History",
            hierarchy=("Overview", "1.3 History"),
            page=8,
        ),
        _chunk(
            "hq",
            "Headquarters and geographic presence across regions.",
            section="Headquarters",
            hierarchy=("Overview", "Headquarters"),
            page=12,
        ),
        _chunk(
            "mission",
            "1.4 Mission\nTo steward our clients' financial lives with precision.",
            section="1.4 Mission",
            hierarchy=("Overview", "1.4 Mission"),
            page=10,
        ),
        _chunk(
            "vision",
            "1.5 Vision\nTo be the most trusted and operationally resilient bank.",
            section="1.5 Vision",
            hierarchy=("Overview", "1.5 Vision"),
            page=10,
        ),
        _chunk(
            "values",
            "1.6 Core Values\nIntegrity First. Client Stewardship. Accountability.",
            section="1.6 Core Values",
            hierarchy=("Overview", "1.6 Core Values"),
            page=10,
        ),
    ]
    plan = plan_answer(question)
    graph = organize_evidence(results, answer_plan=plan)
    composition = compose_answer_evidence(graph, question=question, answer_plan=plan)

    primary_labels = " ".join(item.node.label for item in composition.primary)
    optional_labels = " ".join(item.node.label for item in composition.optional)
    assert "Mission" in primary_labels
    assert "Vision" in primary_labels
    assert "Core Values" in primary_labels
    assert "History" in optional_labels or "Headquarters" in optional_labels

    # Organization unchanged: same chunk ids still present.
    org_ids = {cid for n in graph.nodes for cid in n.chunk_ids}
    comp_ids = {cid for item in composition.all_items for cid in item.node.chunk_ids}
    assert org_ids == comp_ids == {r.chunk_id for r in results}


def test_lifecycle_question_prioritizes_lifecycle_stages() -> None:
    question = "Describe the complete governance journey."
    results = [
        _chunk(
            "hist",
            "Appendix historical notes about early document controls.",
            source="004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf",
            section="Appendix History",
            page=30,
        ),
        _chunk(
            "create",
            "Document creation begins with drafting under the owning function.",
            source="004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf",
            section="Creation",
            page=3,
        ),
        _chunk(
            "approve",
            "Approval is required before publication of controlled documents.",
            source="006_APPROVAL_AUTHORITY_MATRIX.pdf",
            section="Approval",
            page=5,
        ),
        _chunk(
            "retain",
            "Retention schedules define how long records are kept after publication.",
            source="005_RECORDS_RETENTION_POLICY.pdf",
            section="Retention",
            page=12,
        ),
        _chunk(
            "naming",
            "Naming conventions encode department and document type in filenames.",
            source="004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf",
            section="Naming Convention",
            page=8,
        ),
    ]
    plan = plan_answer(question)
    graph = organize_evidence(results, answer_plan=plan)
    composition = compose_answer_evidence(graph, question=question, answer_plan=plan)

    primary = " ".join(item.node.label for item in composition.primary)
    assert "Creation" in primary or "Approval" in primary or "Retention" in primary
    optional = " ".join(item.node.label for item in composition.optional)
    assert "History" in optional or "Appendix" in optional


def test_prompt_builder_uses_composition_tiers() -> None:
    question = "What is Apex National Bank's mission, vision, and core values?"
    results = [
        _chunk(
            "mission",
            "1.4 Mission\nTo steward clients.",
            section="1.4 Mission",
            hierarchy=("Overview", "1.4 Mission"),
        ),
        _chunk(
            "hist",
            "1.3 History\nFounded long ago.",
            section="1.3 History",
            hierarchy=("Overview", "1.3 History"),
        ),
    ]
    plan = plan_answer(question)
    graph = organize_evidence(results, answer_plan=plan)
    composition = compose_answer_evidence(graph, question=question, answer_plan=plan)
    prompt = PromptBuilder().build(
        question,
        results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )
    assert "=== PRIMARY EVIDENCE ===" in prompt.user
    assert "=== OPTIONAL CONTEXT ===" in prompt.user
    assert "Focus the answer on PRIMARY evidence" in prompt.user
    assert "To steward clients." in prompt.user
    assert "Organized evidence graph" not in prompt.user


def test_empty_graph_safe() -> None:
    composition = compose_answer_evidence(None, question="Anything?")
    assert composition.primary == []
    assert "empty_evidence" in composition.decisions
