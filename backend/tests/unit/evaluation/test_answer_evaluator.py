"""Unit tests for answer evaluation modes."""

from __future__ import annotations

from app.evaluation.answer_evaluator import (
    DefaultAnswerEvaluator,
    SemanticAnswerEvaluator,
    get_answer_evaluator,
)
from app.evaluation.schemas import AnswerEvaluationResult, AnswerMatchMode


class _AlwaysPassJudge(DefaultAnswerEvaluator):
    def evaluate(self, *, actual_answer: str, expected_answer: str, mode: AnswerMatchMode):
        return AnswerEvaluationResult(
            mode=mode,
            passed=True,
            actual_answer=actual_answer,
            expected_answer=expected_answer,
            detail="semantic judge passed",
        )


def test_exact_match_passes() -> None:
    evaluator = DefaultAnswerEvaluator()
    result = evaluator.evaluate(
        actual_answer="Singapore",
        expected_answer="Singapore",
        mode=AnswerMatchMode.EXACT,
    )
    assert result.passed is True


def test_exact_match_fails_on_case_difference() -> None:
    evaluator = DefaultAnswerEvaluator()
    result = evaluator.evaluate(
        actual_answer="singapore",
        expected_answer="Singapore",
        mode=AnswerMatchMode.EXACT,
    )
    assert result.passed is False


def test_case_insensitive_match_passes() -> None:
    evaluator = DefaultAnswerEvaluator()
    result = evaluator.evaluate(
        actual_answer="singapore",
        expected_answer="Singapore",
        mode=AnswerMatchMode.CASE_INSENSITIVE,
    )
    assert result.passed is True


def test_contains_match_passes_for_substring() -> None:
    evaluator = DefaultAnswerEvaluator()
    result = evaluator.evaluate(
        actual_answer="The company headquarters is in Singapore.",
        expected_answer="Singapore",
        mode=AnswerMatchMode.CONTAINS,
    )
    assert result.passed is True


def test_contains_match_fails_when_missing() -> None:
    evaluator = DefaultAnswerEvaluator()
    result = evaluator.evaluate(
        actual_answer="The company headquarters is in London.",
        expected_answer="Singapore",
        mode=AnswerMatchMode.CONTAINS,
    )
    assert result.passed is False


def test_semantic_mode_requires_judge() -> None:
    evaluator = DefaultAnswerEvaluator()
    result = evaluator.evaluate(
        actual_answer="Singapore is the HQ.",
        expected_answer="Singapore",
        mode=AnswerMatchMode.SEMANTIC,
    )
    assert result.passed is False
    assert "not configured" in result.detail


def test_semantic_evaluator_uses_registered_judge() -> None:
    evaluator = SemanticAnswerEvaluator(_AlwaysPassJudge())
    result = evaluator.evaluate(
        actual_answer="Different wording",
        expected_answer="Singapore",
        mode=AnswerMatchMode.SEMANTIC,
    )
    assert result.passed is True
    assert result.detail == "semantic judge passed"


def test_get_answer_evaluator_returns_default() -> None:
    evaluator = get_answer_evaluator()
    assert isinstance(evaluator, DefaultAnswerEvaluator)
