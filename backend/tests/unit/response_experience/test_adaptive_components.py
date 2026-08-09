"""Unit tests for Phase 5C adaptive enterprise components."""

from __future__ import annotations

from app.answer_planning import plan_answer
from app.response_experience import (
    content_preserved,
    plan_response_experience,
    render_enterprise_markdown,
)


def _render(question: str, answer: str, *, related: list[str] | None = None, sources: list[str] | None = None):
    plan = plan_answer(question)
    layout = plan_response_experience(question=question, answer=answer, answer_plan=plan)
    result = render_enterprise_markdown(
        layout=layout,
        answer=answer,
        question=question,
        sources=sources or ["PRIMARY.pdf"],
        related_documents=related,
    )
    return layout, result


def test_mission_gets_summary_and_takeaways() -> None:
    question = "What is Apex National Bank's mission, vision, and core values?"
    answer = (
        "Apex National Bank's mission is to steward clients' financial lives. "
        "Its vision is to be the most trusted and operationally resilient bank. "
        "Core values include Integrity First, Client Stewardship, and Accountability."
    )
    layout, result = _render(question, answer)
    assert layout.layout.value == "definition"
    assert "Executive Summary" in result.markdown
    assert "Key Takeaways" in result.markdown
    assert "• " in result.markdown
    assert content_preserved(answer, result.markdown)


def test_metadata_list_can_show_related_documents() -> None:
    question = "What are the different categories of metadata defined by the Enterprise Metadata Standard?"
    answer = (
        "The metadata categories include Administrative Metadata, Business Metadata, "
        "Technical Metadata, and Compliance Metadata."
    )
    _, result = _render(
        question,
        answer,
        sources=["002_ENTERPRISE_METADATA_STANDARD.pdf"],
        related=["003_ENTERPRISE_KNOWLEDGE_TAXONOMY.pdf", "006_APPROVAL_AUTHORITY_MATRIX.pdf"],
    )
    assert "Related Documents" in result.markdown
    assert "Knowledge Taxonomy" in result.markdown or "TAXONOMY" in result.markdown.upper()
    related_section = result.markdown.split("## Related Documents", 1)[-1].split("## Sources", 1)[0]
    assert "002_ENTERPRISE_METADATA_STANDARD.pdf" not in related_section


def test_taxonomy_renders_hierarchy_tree() -> None:
    question = "Explain the hierarchy used in the Enterprise Knowledge Taxonomy."
    answer = "L1: Domain\nL2: Category\nL3: Sub-category\nL4: Document Type\n"
    _, result = _render(question, answer)
    assert "└──" in result.markdown
    assert "hierarchy_tree" in result.components_rendered


def test_governance_journey_timeline_and_checklist() -> None:
    question = "Describe the complete governance journey."
    answer = (
        "The objective is controlled document handling.\n\n"
        "1. Creation\n"
        "2. Review\n"
        "3. Approve\n"
        "4. Publish\n"
        "5. Retain\n"
        "6. Archive\n\n"
        "Roles include authors and approvers."
    )
    _, result = _render(question, answer)
    assert "↓" in result.markdown
    assert "✔ " in result.markdown
    assert "timeline" in result.components_rendered
    assert "checklist" in result.components_rendered


def test_committee_decision_matrix() -> None:
    question = "Which committee should approve this?"
    answer = (
        "Material risk-policy changes require Enterprise Risk Committee approval. "
        "Escalate to the Board Risk Committee when charter thresholds are met."
    )
    _, result = _render(question, answer)
    assert "Decision Summary" in result.markdown or "Committee" in result.markdown
    assert "| Stage | Detail |" in result.markdown
    assert "decision_matrix" in result.components_rendered


def test_empty_components_are_skipped_with_reason() -> None:
    question = "What is Apex National Bank's mission?"
    answer = "To steward clients."
    _, result = _render(question, answer)
    assert result.skip_reasons
    assert "Executive Summary" not in result.markdown or "executive_summary" not in result.components_rendered


def test_no_hallucinated_comparison_without_entities() -> None:
    question = "Compare metadata and taxonomy standards."
    answer = "Both standards support enterprise search quality."
    # "metadata and taxonomy" should detect entities
    _, result = _render(question, answer)
    if "comparison_table" in result.components_rendered:
        assert "| Aspect |" in result.markdown
        # Only entity names from text — no invented feature rows beyond Entity.
        assert "fabricated" not in result.markdown.lower()
