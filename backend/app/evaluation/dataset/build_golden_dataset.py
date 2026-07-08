"""Generate a 100+ case golden evaluation dataset from the GTFS corpus."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND_ROOT))

from app.ingestion.chunker import chunk_text
from app.ingestion.parsers.pdf import PdfParser
from app.ingestion.processor import DefaultDocumentProcessor

CORPUS_DIR = BACKEND_ROOT.parent / "data"
OUTPUT_PATH = BACKEND_ROOT / "app" / "evaluation" / "dataset" / "golden_dataset_full.json"

DOCUMENT_PROFILES: dict[str, dict[str, str]] = {
    "GTFS-EXEC-001": {
        "document_type": "overview",
        "category": "general",
        "prefix": "EXEC",
    },
    "GTFS-HR-001": {
        "document_type": "handbook",
        "category": "hr",
        "prefix": "HR",
    },
    "GTFS-HR-002": {
        "document_type": "policy",
        "category": "hr",
        "prefix": "HR",
    },
    "GTFS-FIN-001": {
        "document_type": "financial_report",
        "category": "finance",
        "prefix": "FIN",
    },
    "GTFS-FIN-002": {
        "document_type": "financial_report",
        "category": "finance",
        "prefix": "FIN",
    },
    "GTFS-FIN-003": {
        "document_type": "financial_report",
        "category": "finance",
        "prefix": "FIN",
    },
    "GTFS-SEC-001": {
        "document_type": "security_policy",
        "category": "security",
        "prefix": "SEC",
    },
    "GTFS-SEC-002": {
        "document_type": "security_policy",
        "category": "security",
        "prefix": "SEC",
    },
    "GTFS-SEC-003": {
        "document_type": "guide",
        "category": "security",
        "prefix": "SEC",
    },
    "GTFS-COMP-001": {
        "document_type": "compliance",
        "category": "security",
        "prefix": "COMP",
    },
    "GTFS-COMP-002": {
        "document_type": "compliance",
        "category": "security",
        "prefix": "COMP",
    },
    "GTFS-OPS-001": {
        "document_type": "procedure",
        "category": "general",
        "prefix": "OPS",
    },
    "GTFS-OPS-002": {
        "document_type": "procedure",
        "category": "general",
        "prefix": "OPS",
    },
    "GTFS-OPS-003": {
        "document_type": "procedure",
        "category": "general",
        "prefix": "OPS",
    },
    "GTFS-LEGAL-001": {
        "document_type": "legal_policy",
        "category": "general",
        "prefix": "LEGAL",
    },
    "GTFS-RISK-001": {
        "document_type": "risk_framework",
        "category": "general",
        "prefix": "RISK",
    },
    "GTFS-BCP-001": {
        "document_type": "business_continuity",
        "category": "general",
        "prefix": "BCP",
    },
    "GTFS-PROC-001": {
        "document_type": "procurement",
        "category": "general",
        "prefix": "PROC",
    },
}

FACT_PATTERNS: list[tuple[str, str, str, str]] = [
    (
        "factual_lookup",
        r"established in (\d{4})",
        "When was GlobalTrust established?",
        "easy",
    ),
    (
        "factual_lookup",
        r"headquartered in ([A-Za-z\s]+?)(?:\.|,|;| with)",
        "Where is GlobalTrust headquartered?",
        "easy",
    ),
    (
        "financial_data",
        r"(FY20\d{2})",
        "Which fiscal year is referenced in this document?",
        "medium",
    ),
    (
        "financial_data",
        r"(SGD\s*[\d,.]+ (?:million|billion|M|B))",
        "What financial amount is stated?",
        "medium",
    ),
    (
        "policy_rule",
        r"(?:must|shall|required to)\s+([^.]{10,80})",
        "What is a stated requirement in this document?",
        "medium",
    ),
    (
        "security_requirement",
        r"(?:MFA|multi-factor authentication|password)",
        "What security control is mentioned?",
        "medium",
    ),
    (
        "compliance_rule",
        r"(?:AML|KYC|anti-money laundering|know your customer)",
        "What compliance topic is covered?",
        "medium",
    ),
    (
        "definition",
        r"([A-Z][A-Za-z\s]{3,40})\s+(?:means|refers to|is defined as)\s+([^.]{10,120})",
        "How is a key term defined?",
        "hard",
    ),
    (
        "procedure_step",
        r"(?:Step\s+\d+|Phase\s+\d+)[:\s]+([^.]{15,100})",
        "What procedural step is described?",
        "medium",
    ),
    (
        "table_query",
        r"(Singapore \(HQ\)|Group headquarters)",
        "What is the primary function of the Singapore office?",
        "medium",
    ),
    (
        "cross_reference",
        r"(GTFS-[A-Z]+-\d{3})",
        "What related GTFS document is referenced?",
        "hard",
    ),
    (
        "factual_lookup",
        r"(\d{1,3}(?:,\d{3})*)\s+employees",
        "How many employees are mentioned?",
        "easy",
    ),
    (
        "factual_lookup",
        r"(Sarah Mitchell|Daniel Carter|Michael Rodriguez|David Chen)",
        "Which executive leader is named?",
        "easy",
    ),
    (
        "policy_rule",
        r"(?:retention period|retain(?:ed)? for)\s+([^.]{10,80})",
        "What retention rule is specified?",
        "hard",
    ),
    (
        "security_requirement",
        r"(?:VPN|virtual private network)",
        "What remote access method is described?",
        "medium",
    ),
]


@dataclass
class FactCandidate:
    query_category: str
    question: str
    expected_answer: str
    difficulty: str
    chunk_index: int
    page_number: int | None
    source_sentence: str


def _profile_for(filename: str) -> dict[str, str]:
    stem = Path(filename).stem
    code = stem.split("_")[0]
    if code in DOCUMENT_PROFILES:
        return DOCUMENT_PROFILES[code]
    prefix = stem.split("-")[1] if "-" in stem else "GEN"
    return {"document_type": "general", "category": "general", "prefix": prefix}


def _clean_answer(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" .,;")
    return cleaned[:120]


def _question_from_category(
    query_category: str,
    answer: str,
    filename: str,
) -> str:
    stem = Path(filename).stem.replace("_", " ")
    templates = {
        "factual_lookup": f"What factual information does {stem} provide about: {answer[:60]}?",
        "policy_rule": f"What policy requirement is stated in {stem}?",
        "financial_data": f"What financial figure appears in {stem}?",
        "procedure_step": f"What procedure is described in {stem}?",
        "security_requirement": f"What security requirement is in {stem}?",
        "compliance_rule": f"What compliance rule applies in {stem}?",
        "table_query": f"According to {stem}, what is the answer regarding: {answer[:50]}?",
        "definition": f"How is a term defined in {stem}?",
        "cross_reference": f"What cross-reference appears in {stem}?",
    }
    return templates.get(query_category, f"What does {stem} say about {answer[:50]}?")


def _extract_candidates(
    filename: str,
    chunks: list,
) -> list[FactCandidate]:
    candidates: list[FactCandidate] = []
    seen_answers: set[str] = set()

    for chunk in chunks:
        text = chunk.content
        for query_category, pattern, question_template, difficulty in FACT_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if match.lastindex and match.lastindex >= 2:
                    answer = _clean_answer(match.group(2))
                elif match.lastindex and match.lastindex >= 1:
                    answer = _clean_answer(match.group(1))
                else:
                    answer = _clean_answer(match.group(0))
                if len(answer) < 3 or answer.casefold() in seen_answers:
                    continue
                seen_answers.add(answer.casefold())

                if "{" not in question_template:
                    question = question_template
                else:
                    question = _question_from_category(query_category, answer, filename)

                candidates.append(
                    FactCandidate(
                        query_category=query_category,
                        question=question,
                        expected_answer=answer,
                        difficulty=difficulty,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        source_sentence=text[:200],
                    )
                )
                if len(candidates) >= 8:
                    return candidates
    return candidates


def build_dataset(*, min_cases: int = 100) -> dict:
    """Build the full golden dataset payload."""
    parser = PdfParser()
    cases: list[dict] = []
    case_counter = 0

    pdf_files = sorted(CORPUS_DIR.glob("*.pdf"))
    for pdf_path in pdf_files:
        profile = _profile_for(pdf_path.name)
        raw = parser.parse(pdf_path.read_bytes(), pdf_path.name)
        normalized = DefaultDocumentProcessor.normalize_text(raw)
        chunks = chunk_text(normalized, pdf_path.name, profile["category"])
        candidates = _extract_candidates(pdf_path.name, chunks)

        for candidate in candidates:
            case_counter += 1
            case_id = f"{profile['prefix']}-{case_counter:03d}"
            cases.append(
                {
                    "id": case_id,
                    "question": candidate.question,
                    "expected_answer": candidate.expected_answer,
                    "expected_document": pdf_path.name,
                    "expected_page": candidate.page_number,
                    "expected_chunks": [candidate.chunk_index],
                    "category": profile["category"],
                    "difficulty": candidate.difficulty,
                    "document_type": profile["document_type"],
                    "query_category": candidate.query_category,
                    "tags": [profile["document_type"], candidate.query_category],
                    "answer_match_mode": "contains",
                    "role": "admin",
                    "authorized_sources": [pdf_path.name],
                    "notes": candidate.source_sentence[:160],
                }
            )

    # Pad with sentence-based factual lookups if below minimum
    if len(cases) < min_cases:
        for pdf_path in pdf_files:
            if len(cases) >= min_cases:
                break
            profile = _profile_for(pdf_path.name)
            raw = parser.parse(pdf_path.read_bytes(), pdf_path.name)
            normalized = DefaultDocumentProcessor.normalize_text(raw)
            chunks = chunk_text(normalized, pdf_path.name, profile["category"])
            for chunk in chunks:
                sentences = re.split(r"(?<=[.!?])\s+", chunk.content)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) < 40 or len(sentence) > 180:
                        continue
                    if "Page " in sentence and "of " in sentence:
                        continue
                    case_counter += 1
                    cases.append(
                        {
                            "id": f"{profile['prefix']}-{case_counter:03d}",
                            "question": (
                                f"According to {pdf_path.stem.replace('_', ' ')}, "
                                f"what is stated about: {sentence[:50]}?"
                            ),
                            "expected_answer": sentence[:80],
                            "expected_document": pdf_path.name,
                            "expected_page": chunk.page_number,
                            "expected_chunks": [chunk.chunk_index],
                            "category": profile["category"],
                            "difficulty": "hard",
                            "document_type": profile["document_type"],
                            "query_category": "factual_lookup",
                            "tags": [profile["document_type"], "auto_generated"],
                            "answer_match_mode": "contains",
                            "role": "admin",
                            "authorized_sources": [pdf_path.name],
                        }
                    )
                    if len(cases) >= min_cases:
                        break

    breakdown: dict[str, dict[str, int]] = {
        "by_document_type": {},
        "by_difficulty": {},
        "by_query_category": {},
    }
    for case in cases:
        breakdown["by_document_type"][case["document_type"]] = (
            breakdown["by_document_type"].get(case["document_type"], 0) + 1
        )
        breakdown["by_difficulty"][case["difficulty"]] = (
            breakdown["by_difficulty"].get(case["difficulty"], 0) + 1
        )
        breakdown["by_query_category"][case["query_category"]] = (
            breakdown["by_query_category"].get(case["query_category"], 0) + 1
        )

    return {
        "version": "2.0.0",
        "description": (
            "Full golden evaluation dataset with 100+ cases across the GTFS corpus. "
            "Organized by document type, difficulty, and query category."
        ),
        "metadata": {
            "corpus": str(CORPUS_DIR),
            "case_count": len(cases),
            "breakdown": breakdown,
            "generator": "build_golden_dataset.py",
        },
        "cases": cases,
    }


def main() -> None:
    payload = build_dataset(min_cases=100)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['cases'])} cases to {OUTPUT_PATH}")
    print("Breakdown:", json.dumps(payload["metadata"]["breakdown"], indent=2))


if __name__ == "__main__":
    main()
