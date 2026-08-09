"""Unit tests for Phase 5B enterprise markdown renderer."""

from __future__ import annotations

from app.answer_planning import plan_answer
from app.response_experience import (
    content_preserved,
    plan_response_experience,
    render_enterprise_markdown,
)
from app.response_experience.ordering import COMPONENT_RENDER_PRIORITY, compute_render_order
from app.response_experience.enums import ResponseComponent


def test_render_order_is_deterministic_by_priority() -> None:
    components = (
        ResponseComponent.SOURCES,
        ResponseComponent.DEFINITION,
        ResponseComponent.EXECUTIVE_SUMMARY,
        ResponseComponent.TITLE,
    )
    ordered = compute_render_order(components)
    assert ordered[0] == ResponseComponent.TITLE
    assert ordered[1] == ResponseComponent.EXECUTIVE_SUMMARY
    assert ordered[2] == ResponseComponent.DEFINITION
    assert ordered[-1] == ResponseComponent.SOURCES
    assert COMPONENT_RENDER_PRIORITY[ResponseComponent.EXECUTIVE_SUMMARY] == 100


def test_layout_includes_render_order() -> None:
    plan = plan_answer("What is Apex National Bank's mission, vision, and core values?")
    layout = plan_response_experience(
        question="What is Apex National Bank's mission, vision, and core values?",
        answer="Mission is to steward clients. Vision is trust. Values include integrity.",
        answer_plan=plan,
    )
    assert layout.render_order
    assert layout.render_order[0] == ResponseComponent.TITLE
    assert layout.component_priorities
    payload = layout.to_dict()
    assert payload["render_order"]
    assert "title" in payload["component_priorities"]


def test_definition_render_preserves_content() -> None:
    question = "What is Apex National Bank's mission, vision, and core values?"
    answer = (
        "Apex National Bank's mission is to steward clients' financial lives. "
        "Its vision is to be the most trusted bank. "
        "Core values include Integrity First and Client Stewardship."
    )
    plan = plan_answer(question)
    layout = plan_response_experience(question=question, answer=answer, answer_plan=plan)
    result = render_enterprise_markdown(
        layout=layout,
        answer=answer,
        question=question,
        sources=["COMPANY_PROFILE.pdf"],
    )
    assert result.markdown.startswith("# ")
    assert "## Definition" in result.markdown or "## " in result.markdown
    assert "## Sources" in result.markdown
    assert "COMPANY_PROFILE.pdf" in result.markdown
    assert content_preserved(answer, result.markdown)
    assert "steward clients" in result.markdown


def test_workflow_render_uses_steps_heading() -> None:
    question = "Describe the complete governance journey."
    answer = (
        "The objective is controlled document handling.\n\n"
        "1. Creation\n"
        "2. Approval\n"
        "3. Retention\n\n"
        "Roles include document owners and approvers. "
        "The outcome is durable, governed records."
    )
    plan = plan_answer(question)
    layout = plan_response_experience(question=question, answer=answer, answer_plan=plan)
    result = render_enterprise_markdown(
        layout=layout,
        answer=answer,
        question=question,
        sources=["005_RECORDS_RETENTION_POLICY.pdf"],
    )
    assert layout.layout.value == "workflow"
    assert "Workflow Steps" in result.markdown or "Objective" in result.markdown
    assert content_preserved(answer, result.markdown)
    assert result.template_used == "workflow_v1"


def test_hierarchy_tree_formatting() -> None:
    question = "Explain the hierarchy used in the Enterprise Knowledge Taxonomy."
    answer = (
        "L1: Domain\n"
        "L2: Category\n"
        "L3: Sub-category\n"
        "L4: Document Type\n"
    )
    plan = plan_answer(question)
    layout = plan_response_experience(question=question, answer=answer, answer_plan=plan)
    result = render_enterprise_markdown(
        layout=layout,
        answer=answer,
        question=question,
        sources=["003_ENTERPRISE_KNOWLEDGE_TAXONOMY.pdf"],
    )
    assert layout.layout.value == "hierarchy"
    assert "└──" in result.markdown
    assert "Domain" in result.markdown
    assert "Document Type" in result.markdown


def test_short_answer_skips_executive_summary_component() -> None:
    question = "What is Apex National Bank's mission?"
    answer = "To steward clients' financial lives with precision."
    plan = plan_answer(question)
    layout = plan_response_experience(question=question, answer=answer, answer_plan=plan)
    result = render_enterprise_markdown(
        layout=layout,
        answer=answer,
        question=question,
        sources=["COMPANY_PROFILE.pdf"],
    )
    assert "Executive Summary" not in result.markdown
    assert content_preserved(answer, result.markdown)


def test_renderer_does_not_guess_layout() -> None:
    question = "What are the different categories of metadata?"
    answer = "Administrative, Business, Technical, and Compliance metadata."
    plan = plan_answer(question)
    layout = plan_response_experience(question=question, answer=answer, answer_plan=plan)
    result = render_enterprise_markdown(layout=layout, answer=answer, question=question)
    assert result.layout == layout.layout.value
    assert result.layout == "list_extraction"
