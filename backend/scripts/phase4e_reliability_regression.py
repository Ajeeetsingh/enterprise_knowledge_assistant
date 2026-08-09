"""Phase 4E — Answer reliability / intent coverage / confidence regression.

Synthetic answers + GAQA only (no LLM, no retrieval index mutation).
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.answer_planning import plan_answer
from app.evidence_composition import compose_answer_evidence
from app.evidence_organization import organize_evidence
from app.gaqa import run_gaqa
from app.rag.types import RetrievalResult


def _c(
    chunk_id: str,
    content: str,
    *,
    source: str,
    section: str,
    page: int = 1,
) -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source=source,
        category="general",
        confidence=0.8,
        chunk_id=chunk_id,
        page_number=page,
        section_title=section,
        hierarchy_path=(section,),
        chunk_type="subsection",
    )


def _run(question: str, answer: str, results: list[RetrievalResult]):
    plan = plan_answer(question)
    graph = organize_evidence(results, answer_plan=plan)
    composition = compose_answer_evidence(graph, question=question, answer_plan=plan)
    return run_gaqa(
        question=question,
        answer=answer,
        results=results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )


def main() -> int:
    failures: list[str] = []

    # 1) Unknown ChatGPT policy — related docs, refuse.
    q1 = "What is Apex National Bank's policy for employees using ChatGPT?"
    r1 = [
        _c(
            "g",
            "Enterprise governance and taxonomy oversight by committees.",
            source="GOVERNANCE.pdf",
            section="Governance",
        ),
        _c(
            "m",
            "Metadata categories: administrative, business, technical.",
            source="METADATA.pdf",
            section="Categories",
        ),
    ]
    rep1 = _run(
        q1,
        "Employees should follow governance standards for technology use.",
        r1,
    )
    if rep1.answer_completeness != "related_not_answering":
        failures.append(f"chatgpt completeness={rep1.answer_completeness}")
    if rep1.overall_confidence > 0.20:
        failures.append(f"chatgpt confidence too high={rep1.overall_confidence}")
    if not rep1.recommended_final_answer or "couldn't find" not in (
        rep1.recommended_final_answer or ""
    ).lower():
        failures.append("chatgpt missing refusal message")

    # 2) Complete mission/vision/values — high confidence.
    q2 = "What is Apex National Bank's mission, vision, and core values?"
    r2 = [
        _c("m", "1.4 Mission To steward clients.", source="PROFILE.pdf", section="Mission"),
        _c("v", "1.5 Vision Most trusted bank.", source="PROFILE.pdf", section="Vision"),
        _c(
            "c",
            "1.6 Core Values Integrity First. Client Stewardship.",
            source="PROFILE.pdf",
            section="Core Values",
        ),
    ]
    a2 = (
        "Mission: To steward clients. Vision: Most trusted bank. "
        "Core values include Integrity First and Client Stewardship."
    )
    rep2 = _run(q2, a2, r2)
    if rep2.answer_completeness != "complete":
        failures.append(f"mission completeness={rep2.answer_completeness}")
    if rep2.overall_confidence < 0.80:
        failures.append(f"mission confidence too low={rep2.overall_confidence}")

    # 3) Partial mission — medium confidence + note.
    a3 = "Mission: To steward clients. Vision: Most trusted bank."
    rep3 = _run(q2, a3, r2)
    if rep3.answer_completeness != "partial":
        failures.append(f"partial completeness={rep3.answer_completeness}")
    if not (0.45 <= rep3.overall_confidence <= 0.80):
        failures.append(f"partial confidence out of band={rep3.overall_confidence}")
    if not rep3.recommended_final_answer or "could not find" not in (
        rep3.recommended_final_answer or ""
    ).lower():
        failures.append("partial missing honesty note")

    # 4) Unknown salary policy.
    q4 = "What is the employee salary banding policy?"
    r4 = [
        _c(
            "hr",
            "HR handbook covers workplace conduct and reporting channels.",
            source="HR.pdf",
            section="Conduct",
        ),
    ]
    rep4 = _run(q4, "Compensation follows market practice.", r4)
    if rep4.answer_completeness not in {"related_not_answering", "explicit_refusal"}:
        failures.append(f"salary completeness={rep4.answer_completeness}")
    if rep4.overall_confidence > 0.20:
        failures.append(f"salary confidence too high={rep4.overall_confidence}")

    # 5) Explicit refusal must stay low confidence.
    rep5 = _run(
        q1,
        "I couldn't find any document that defines this policy.",
        r1,
    )
    if rep5.overall_confidence > 0.20:
        failures.append(f"refusal confidence too high={rep5.overall_confidence}")

    # 6) Diagnostics present.
    for label, rep in (("chatgpt", rep1), ("mission", rep2), ("partial", rep3)):
        payload = rep.to_dict()
        for key in (
            "intent_coverage",
            "evidence_specificity",
            "answer_completeness",
            "overall_reliability_score",
            "confidence_breakdown",
        ):
            if key not in payload:
                failures.append(f"{label} missing diagnostic key {key}")

    if failures:
        print("FAIL Phase 4E reliability regression:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS Phase 4E reliability regression")
    print(
        f"  chatgpt: completeness={rep1.answer_completeness} "
        f"conf={rep1.overall_confidence:.3f} intent={rep1.intent_coverage:.3f}"
    )
    print(
        f"  complete: completeness={rep2.answer_completeness} "
        f"conf={rep2.overall_confidence:.3f}"
    )
    print(
        f"  partial: completeness={rep3.answer_completeness} "
        f"conf={rep3.overall_confidence:.3f}"
    )
    print(
        f"  salary: completeness={rep4.answer_completeness} "
        f"conf={rep4.overall_confidence:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
