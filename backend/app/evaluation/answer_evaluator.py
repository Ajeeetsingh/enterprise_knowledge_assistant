"""Answer evaluation strategies for benchmark cases."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.evaluation.schemas import AnswerEvaluationResult, AnswerMatchMode


class AnswerEvaluator(ABC):
    """Evaluate generated answers against expected answers."""

    @abstractmethod
    def evaluate(
        self,
        *,
        actual_answer: str,
        expected_answer: str,
        mode: AnswerMatchMode,
    ) -> AnswerEvaluationResult:
        """Return whether the generated answer satisfies the expected answer."""


class DefaultAnswerEvaluator(AnswerEvaluator):
    """Built-in answer evaluation modes."""

    def evaluate(
        self,
        *,
        actual_answer: str,
        expected_answer: str,
        mode: AnswerMatchMode,
    ) -> AnswerEvaluationResult:
        actual = actual_answer.strip()
        expected = expected_answer.strip()

        if mode is AnswerMatchMode.EXACT:
            passed = actual == expected
            detail = "Exact string match." if passed else "Answers differ."
        elif mode is AnswerMatchMode.CASE_INSENSITIVE:
            passed = actual.casefold() == expected.casefold()
            detail = (
                "Case-insensitive exact match."
                if passed
                else "Answers differ after case normalization."
            )
        elif mode is AnswerMatchMode.CONTAINS:
            passed = expected.casefold() in actual.casefold()
            detail = (
                f"Expected answer found in generated answer."
                if passed
                else f"Expected answer '{expected}' not found in generated answer."
            )
        elif mode is AnswerMatchMode.SEMANTIC:
            passed = False
            detail = (
                "Semantic evaluation is not configured. "
                "Register an LLM judge via SemanticAnswerEvaluator."
            )
        else:
            raise ValueError(f"Unsupported answer match mode: {mode}")

        return AnswerEvaluationResult(
            mode=mode,
            passed=passed,
            actual_answer=actual,
            expected_answer=expected,
            detail=detail,
        )


class SemanticAnswerEvaluator(AnswerEvaluator):
    """Pluggable semantic evaluator for future LLM-judge integration."""

    def __init__(self, judge: AnswerEvaluator) -> None:
        self._judge = judge

    def evaluate(
        self,
        *,
        actual_answer: str,
        expected_answer: str,
        mode: AnswerMatchMode,
    ) -> AnswerEvaluationResult:
        if mode is AnswerMatchMode.SEMANTIC:
            return self._judge.evaluate(
                actual_answer=actual_answer,
                expected_answer=expected_answer,
                mode=mode,
            )
        return DefaultAnswerEvaluator().evaluate(
            actual_answer=actual_answer,
            expected_answer=expected_answer,
            mode=mode,
        )


def get_answer_evaluator(semantic_judge: AnswerEvaluator | None = None) -> AnswerEvaluator:
    """Return the configured answer evaluator."""
    if semantic_judge is not None:
        return SemanticAnswerEvaluator(semantic_judge)
    return DefaultAnswerEvaluator()
