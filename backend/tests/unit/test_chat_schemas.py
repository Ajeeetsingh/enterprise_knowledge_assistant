"""Unit tests for chat API request schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.chat import QUESTION_MAX_LENGTH, ChatAskRequest


def test_valid_question_is_accepted() -> None:
    request = ChatAskRequest(question="  What is the leave policy?  ")

    assert request.question == "What is the leave policy?"


def test_empty_question_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ChatAskRequest(question="")


def test_whitespace_only_question_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ChatAskRequest(question="   ")


def test_question_exceeding_max_length_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ChatAskRequest(question="a" * (QUESTION_MAX_LENGTH + 1))


def test_question_at_max_length_is_accepted() -> None:
    question = "a" * QUESTION_MAX_LENGTH
    request = ChatAskRequest(question=question)

    assert request.question == question
