"""Capture and persist per-question benchmark artifacts for post-mortem analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.evaluation.schemas import QuestionArtifact
from app.rag.types import Citation, RetrievalResult


def build_question_artifact(
    *,
    case_id: str,
    question: str,
    expected_answer: str,
    actual_answer: str,
    retrieval_results: list[RetrievalResult],
    prompt_system: str,
    prompt_user: str,
    citations: list[Citation],
    generation_backend: str | None,
) -> QuestionArtifact:
    """Assemble a complete artifact record for one benchmark case."""
    retrieved_chunks = [
        {
            "rank": index,
            "chunk_id": result.chunk_id,
            "source": result.source,
            "page_number": result.page_number,
            "category": result.category,
            "confidence": result.confidence,
            "content": result.content,
        }
        for index, result in enumerate(retrieval_results, start=1)
    ]
    return QuestionArtifact(
        case_id=case_id,
        question=question,
        expected_answer=expected_answer,
        actual_answer=actual_answer,
        prompt_system=prompt_system,
        prompt_user=prompt_user,
        retrieved_chunks=retrieved_chunks,
        citations=[
            {
                "source": citation.source,
                "page": citation.page,
                "excerpt": citation.excerpt,
                "confidence": citation.confidence,
            }
            for citation in citations
        ],
        generation_backend=generation_backend,
    )


def save_question_artifact(
    artifact: QuestionArtifact,
    *,
    artifacts_dir: Path,
) -> Path:
    """Persist a single question artifact as JSON."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / f"{artifact.case_id}.json"
    path.write_text(json.dumps(artifact.to_dict(), indent=2), encoding="utf-8")
    return path


def load_question_artifact(path: Path) -> dict[str, Any]:
    """Load a persisted question artifact."""
    return json.loads(path.read_text(encoding="utf-8"))
