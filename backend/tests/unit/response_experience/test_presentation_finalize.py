"""Unit tests for Phase 5E final UX polish & consistency."""

from __future__ import annotations

from app.answer_planning import plan_answer
from app.response_experience import (
    content_preserved,
    finalize_enterprise_markdown,
    plan_response_experience,
    polish_enterprise_markdown,
    render_enterprise_markdown,
)


def _pipeline(question: str, answer: str, *, sources: list[str] | None = None) -> str:
    plan = plan_answer(question)
    layout = plan_response_experience(question=question, answer=answer, answer_plan=plan)
    rendered = render_enterprise_markdown(
        layout=layout,
        answer=answer,
        question=question,
        sources=sources or ["COMPANY_PROFILE.pdf", "GOVERNANCE.pdf"],
    )
    polished = polish_enterprise_markdown(rendered.markdown)
    finalized = finalize_enterprise_markdown(polished.markdown)
    return finalized.markdown


def test_finalize_preserves_answer_content() -> None:
    question = "What is Apex National Bank's mission, vision, and core values?"
    answer = (
        "Apex National Bank's mission is to steward clients' financial lives. "
        "Its vision is to be the most trusted and operationally resilient bank. "
        "Core values include Integrity First, Client Stewardship, and Accountability."
    )
    final = _pipeline(question, answer)
    assert content_preserved(answer, final)
    assert final.startswith("# ")
    assert "#### " not in final


def test_empty_sections_removed() -> None:
    raw = (
        "# Title\n\n"
        "## Executive Summary\n\n"
        "_none_\n\n"
        "## Mission\n\n"
        "Serve clients with integrity.\n\n"
        "## Related Documents\n\n"
        "\n"
        "## Sources\n\n"
        "- Zebra.pdf\n"
        "- Alpha.pdf\n"
        "- Alpha.pdf\n"
    )
    result = finalize_enterprise_markdown(raw)
    assert "## Executive Summary" not in result.markdown
    assert "## Related Documents" not in result.markdown
    assert "## Mission" in result.markdown
    assert result.empty_sections_removed >= 1


def test_sources_deduped_and_sorted() -> None:
    raw = (
        "# Title\n\n"
        "## Answer\n\n"
        "Body text here.\n\n"
        "## Sources\n\n"
        "- Zebra Guide.pdf\n"
        "- *Alpha Standard.pdf*\n"
        "- Zebra Guide.pdf\n"
        "- beta notes.pdf\n"
    )
    result = finalize_enterprise_markdown(raw)
    sources_idx = result.markdown.index("## Sources")
    block = result.markdown[sources_idx:]
    bullets = [
        line[2:].strip()
        for line in block.splitlines()
        if line.startswith("- ")
    ]
    assert bullets == sorted(bullets, key=str.lower)
    assert len(bullets) == len(set(b.lower() for b in bullets))
    assert "Alpha Standard.pdf" in bullets


def test_separators_between_major_sections_only() -> None:
    raw = (
        "# Title\n\n"
        "## Mission\n\n"
        "Mission text.\n\n"
        "## Vision\n\n"
        "Vision text.\n\n"
        "## Core Values\n\n"
        "- Integrity\n"
        "- Stewardship\n"
    )
    result = finalize_enterprise_markdown(raw)
    text = result.markdown
    assert text.count("\n---\n") >= 1
    # No separator between list items.
    assert "-\n---\n-" not in text.replace(" ", "")


def test_list_and_table_normalization() -> None:
    raw = (
        "# Title\n\n"
        "## Items\n\n"
        "* One\n"
        "+ Two\n"
        "• Three\n\n"
        "## Matrix\n\n"
        "| Role | Action\n"
        "| A | Approve |\n"
    )
    result = finalize_enterprise_markdown(raw)
    assert "- One" in result.markdown
    assert "- Two" in result.markdown
    assert "| Role" in result.markdown
    assert "| ---" in result.markdown or "|---" in result.markdown.replace(" ", "")
    assert result.validation_ok or "malformed table" not in " ".join(
        result.validation_issues
    )


def test_refusal_edge_case_stays_clean() -> None:
    question = "What is the ChatGPT usage policy?"
    answer = (
        "I cannot answer this from the available enterprise knowledge base. "
        "No supporting evidence was retrieved for a ChatGPT policy."
    )
    final = _pipeline(question, answer, sources=[])
    assert content_preserved(answer, final)
    assert final.strip()
    # Short refusals should not end with decorative rules.
    assert not final.strip().endswith("---")


def test_no_double_blank_lines() -> None:
    question = "Describe the complete governance journey."
    answer = (
        "The objective is controlled document handling.\n\n"
        "1. Create\n2. Review\n3. Approve\n4. Publish\n\n"
        "Roles include authors and approvers."
    )
    final = _pipeline(question, answer)
    assert "\n\n\n" not in final
