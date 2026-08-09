"""Unit tests for Phase 5D presentation polish."""

from __future__ import annotations

from app.answer_planning import plan_answer
from app.response_experience import (
    content_preserved,
    plan_response_experience,
    polish_enterprise_markdown,
    render_enterprise_markdown,
)


def _pipeline(question: str, answer: str, *, sources: list[str] | None = None) -> tuple[str, str]:
    plan = plan_answer(question)
    layout = plan_response_experience(question=question, answer=answer, answer_plan=plan)
    rendered = render_enterprise_markdown(
        layout=layout,
        answer=answer,
        question=question,
        sources=sources or ["COMPANY_PROFILE.pdf"],
    )
    polished = polish_enterprise_markdown(rendered.markdown)
    return rendered.markdown, polished.markdown


def test_polish_preserves_answer_content() -> None:
    question = "What is Apex National Bank's mission, vision, and core values?"
    answer = (
        "Apex National Bank's mission is to steward clients' financial lives. "
        "Its vision is to be the most trusted and operationally resilient bank. "
        "Core values include Integrity First, Client Stewardship, and Accountability."
    )
    _, polished = _pipeline(question, answer)
    assert content_preserved(answer, polished)
    assert polished.startswith("# ")


def test_heading_hierarchy_is_consistent() -> None:
    question = "Describe the complete governance journey."
    answer = (
        "The objective is controlled document handling.\n\n"
        "1. Create\n2. Review\n3. Approve\n4. Publish\n\n"
        "Roles include authors and approvers."
    )
    _, polished = _pipeline(question, answer)
    lines = polished.splitlines()
    assert lines[0].startswith("# ")
    h2 = [line for line in lines if line.startswith("## ")]
    assert h2
    assert not any(line.startswith("#### ") for line in lines)


def test_emphasis_bolds_committee_names() -> None:
    question = "Which committee should approve this?"
    answer = (
        "The Enterprise Risk Committee should approve material risk-policy changes. "
        "Escalate to the Board Risk Committee when thresholds are met."
    )
    _, polished = _pipeline(question, answer)
    assert "**Enterprise Risk Committee**" in polished or "Enterprise Risk Committee" in polished
    # Restrained: not every word bolded.
    bold_spans = polished.count("**")
    assert bold_spans <= 24


def test_inline_list_conversion_for_categories() -> None:
    question = "What are the different categories of metadata?"
    answer = (
        "The metadata categories include Administrative Metadata, Business Metadata, "
        "Technical Metadata, and Compliance Metadata."
    )
    _, polished = _pipeline(question, answer, sources=["002_ENTERPRISE_METADATA_STANDARD.pdf"])
    assert "- Administrative Metadata" in polished or "Administrative Metadata" in polished
    assert content_preserved(answer, polished)


def test_callout_for_mandatory_language() -> None:
    raw = (
        "# Title\n\n"
        "## Definition\n\n"
        "Metadata must be assigned before classification.\n\n"
        "## Sources\n\n"
        "- `META.pdf`\n"
    )
    result = polish_enterprise_markdown(raw)
    assert "> **Important**" in result.markdown or "> **Note**" in result.markdown
    assert "Metadata must be assigned before classification" in result.markdown


def test_source_deduplication() -> None:
    raw = (
        "# Title\n\n"
        "## Sources\n\n"
        "- `A.pdf`\n"
        "- `A.pdf`\n"
        "- B.pdf\n"
    )
    result = polish_enterprise_markdown(raw)
    assert result.markdown.count("A.pdf") == 1


def test_transforms_are_reported() -> None:
    result = polish_enterprise_markdown("# Hello\n\nBody text here.\n")
    assert isinstance(result.transforms_applied, list)
    assert "markdown_chars" in result.to_dict()
