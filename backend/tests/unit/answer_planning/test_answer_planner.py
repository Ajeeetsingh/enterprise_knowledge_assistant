"""Unit tests for Phase 4A answer planning."""

from __future__ import annotations

import pytest

from app.answer_planning import AnswerType, plan_answer
from app.answer_planning.blueprints import all_blueprints
from app.answer_planning.classifier import classify_answer_type
from app.llm.prompt_builder import PromptBuilder
from app.rag.types import RetrievalResult


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What is the Records Retention Policy?", AnswerType.DEFINITION),
        (
            "Explain how document identifiers, filenames, and versioning work together.",
            AnswerType.RELATIONSHIP,
        ),
        ("Describe the complete governance journey.", AnswerType.WORKFLOW),
        (
            "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
            AnswerType.LIST_EXTRACTION,
        ),
        ("Which committee should approve this?", AnswerType.DECISION_GUIDANCE),
        (
            "What is Apex National Bank's mission, vision, and core values?",
            AnswerType.DEFINITION,
        ),
        (
            "Explain the hierarchy used in the Enterprise Knowledge Taxonomy and how it supports enterprise search.",
            AnswerType.RELATIONSHIP,
        ),
        ("Compare policy documents and standards.", AnswerType.COMPARISON),
        ("Summarize the Approval Authority Matrix.", AnswerType.SUMMARY),
        ("What compliance obligations apply to records retention?", AnswerType.COMPLIANCE),
        ("Where is the document ID format defined?", AnswerType.REFERENCE_LOOKUP),
        (
            "What does the Records Retention Policy require for legal holds?",
            AnswerType.POLICY_LOOKUP,
        ),
        ("What is the Enterprise Committee Charter governance model?", AnswerType.GOVERNANCE),
    ],
)
def test_classifies_foundation_and_governance_questions(
    question: str, expected: AnswerType
) -> None:
    decision = classify_answer_type(question)
    assert decision.answer_type == expected


def test_every_answer_type_has_blueprint() -> None:
    catalog = all_blueprints()
    assert set(catalog) == set(AnswerType)
    for answer_type, blueprint in catalog.items():
        assert blueprint.answer_type == answer_type
        assert len(blueprint.sections) >= 3
        assert blueprint.blueprint_key.endswith("_v1")


def test_plan_answer_is_deterministic_and_structure_only() -> None:
    question = "Describe the complete governance journey."
    first = plan_answer(question)
    second = plan_answer(question)
    assert first == second
    assert first.answer_type == AnswerType.WORKFLOW
    assert first.blueprint.blueprint_key == "Workflow_v1"
    assert "journey" in first.reason.lower() or "complete" in first.reason.lower()
    rendered = first.format_for_prompt()
    assert "Recommended structure:" in rendered
    assert "do not invent facts" in rendered.lower()
    assert "Ordered steps" in rendered


def test_prompt_builder_includes_answer_plan_without_changing_grounding() -> None:
    plan = plan_answer(
        "Explain how document identifiers, filenames, and versioning work together."
    )
    chunk = RetrievalResult(
        content="Document identifiers and filenames share a controlled vocabulary.",
        source="naming.pdf",
        category="general",
        confidence=0.9,
        chunk_id="c1",
        page_number=3,
    )
    prompt = PromptBuilder().build(
        "Explain how document identifiers, filenames, and versioning work together.",
        [chunk],
        answer_plan=plan,
    )
    assert "Question type: Relationship" in prompt.user
    assert "Blueprint: Relationship_v1" in prompt.user
    assert "Explain how they relate" in prompt.user
    assert "ONLY the retrieved" in prompt.user
    assert "naming.pdf" in prompt.user
    assert "Never invent" in prompt.system


def test_different_types_produce_different_structures() -> None:
    definition = plan_answer("What is the Records Retention Policy?")
    workflow = plan_answer("Describe the complete governance journey.")
    listing = plan_answer("What are the different categories of metadata?")
    assert definition.blueprint.sections != workflow.blueprint.sections
    assert workflow.blueprint.sections != listing.blueprint.sections
    assert definition.blueprint.sections[0] == "Short definition"
    assert workflow.blueprint.sections[1] == "Ordered steps"
    assert listing.blueprint.sections[0] == "Direct answer list"
