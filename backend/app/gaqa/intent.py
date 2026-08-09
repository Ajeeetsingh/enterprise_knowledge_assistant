"""Intent coverage and evidence-specificity checks (Phase 4E)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.gaqa.concepts import contains_concept, extract_question_concepts, tokenize
from app.rag.types import RetrievalResult

_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "what",
        "when",
        "where",
        "which",
        "who",
        "how",
        "does",
        "did",
        "are",
        "is",
        "was",
        "were",
        "can",
        "could",
        "should",
        "would",
        "about",
        "from",
        "into",
        "that",
        "this",
        "these",
        "those",
        "their",
        "there",
        "have",
        "has",
        "had",
        "any",
        "our",
        "you",
        "your",
        "a",
        "an",
        "of",
        "to",
        "in",
        "on",
        "by",
        "or",
        "as",
        "at",
        "be",
        "it",
        "its",
        "please",
        "tell",
        "explain",
        "describe",
        "define",
        "defined",
        "different",
        "complete",
        "company",
        "bank",
        "apex",
        "national",
        "organization",
        "enterprise",
        "using",
        "use",
        "used",
        "employees",
        "employee",
        "policy",
        "policies",
        "procedure",
        "standard",
        "standards",
    }
)

# Distinctive subject markers that must appear in evidence when asked.
_SUBJECT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("chatgpt", re.compile(r"\b(chatgpt|chat gpt|openai|gpt-?\d)\b", re.I)),
    ("personal_ai", re.compile(r"\b(personal ai|generative ai|ai assistant|llm)\b", re.I)),
    ("salary", re.compile(r"\b(salary|compensation|bonus|payroll)\b", re.I)),
    ("vpn", re.compile(r"\b(vpn|remote access gateway)\b", re.I)),
    ("password", re.compile(r"\b(password|passphrase|credentials?)\b", re.I)),
    ("leave", re.compile(r"\b(parental leave|pto|vacation|sick leave)\b", re.I)),
    ("crypto", re.compile(r"\b(cryptocurrency|bitcoin|crypto trading)\b", re.I)),
)

_REFUSAL_RE = re.compile(
    r"\b("
    r"could(?:\s*|\s+)not find|"
    r"couldn't find|"
    r"no (?:document|documents|information|policy)|"
    r"not (?:found|available|defined) in|"
    r"do not have (?:enough|any)|"
    r"insufficient"
    r")\b",
    re.I,
)

_DOC_ENUM_RE = re.compile(
    r"(?:according to|per|from)\s+[A-Za-z0-9_\-]+\.pdf|"
    r"[A-Za-z0-9_\-]+\.pdf\s+(?:states?|says?|notes?|explains?|describes?)|"
    r"\bdocument\s+[a-c]\s+says\b",
    re.I,
)


@dataclass(frozen=True)
class IntentAssessment:
    intent_terms: tuple[str, ...]
    subject_markers: tuple[str, ...]
    intent_coverage: float
    evidence_specificity: float
    question_match: float
    intent_covered: bool
    explicit_refusal: bool
    multi_document_enumeration: bool
    reasons: tuple[str, ...]


def extract_intent_terms(question: str) -> list[str]:
    """Distinctive content terms from the question (tenant-agnostic)."""
    tokens = sorted(tokenize(question))
    return [tok for tok in tokens if tok not in _STOPWORDS and len(tok) >= 3]


def detect_subject_markers(question: str) -> list[str]:
    text = question or ""
    return [name for name, pattern in _SUBJECT_PATTERNS if pattern.search(text)]


def is_explicit_refusal(answer: str) -> bool:
    return bool(_REFUSAL_RE.search(answer or ""))


def has_multi_document_enumeration(answer: str) -> bool:
    matches = _DOC_ENUM_RE.findall(answer or "")
    return len(matches) >= 2


def _enrich_evidence(evidence_text: str, results: list[RetrievalResult]) -> str:
    """Include section titles and source names so intent matching sees doc context."""
    extras: list[str] = [evidence_text or ""]
    for item in results:
        extras.append(item.source or "")
        extras.append(item.section_title or "")
        extras.append(" ".join(item.hierarchy_path or ()))
    return "\n".join(extras)


def _term_in_text(term: str, text: str) -> bool:
    """Soft term match: exact token or shared stem prefix (>=4 chars)."""
    if not term:
        return False
    if term in text:
        return True
    if len(term) >= 4:
        stem = term[:4]
        return any(tok.startswith(stem) or stem.startswith(tok[:4]) for tok in text.split())
    return False


def assess_intent_coverage(
    *,
    question: str,
    answer: str,
    evidence_text: str,
    results: list[RetrievalResult],
) -> IntentAssessment:
    """Score whether retrieved evidence actually covers the asked intent."""
    intent_terms = extract_intent_terms(question)
    subjects = detect_subject_markers(question)
    enriched = _enrich_evidence(evidence_text, results)
    evidence_l = enriched.lower()
    answer_l = (answer or "").lower()
    reasons: list[str] = []

    # Subject markers are hard requirements when present in the question.
    subject_hits = 0
    for marker in subjects:
        pattern = next(p for name, p in _SUBJECT_PATTERNS if name == marker)
        if pattern.search(enriched):
            subject_hits += 1
        else:
            reasons.append(f"subject_missing_in_evidence={marker}")
    if subjects:
        subject_coverage = subject_hits / len(subjects)
    else:
        subject_coverage = 1.0

    if intent_terms:
        term_hits = sum(1 for term in intent_terms if _term_in_text(term, evidence_l))
        term_coverage = term_hits / len(intent_terms)
        reasons.append(f"intent_term_hits={term_hits}/{len(intent_terms)}")
    else:
        term_coverage = 0.5

    # Prefer primary-looking overlap with question terms in top retrieved chunks.
    top_text = _enrich_evidence(
        " ".join((item.content or "")[:500] for item in results[:5]),
        results[:5],
    ).lower()
    if intent_terms:
        top_hits = sum(1 for term in intent_terms if _term_in_text(term, top_text))
        specificity = top_hits / len(intent_terms)
    else:
        specificity = 0.5
    if subjects:
        specificity = min(specificity, subject_coverage)

    # Question match: does the answer engage the asked terms?
    if intent_terms:
        answer_term_hits = sum(1 for term in intent_terms if _term_in_text(term, answer_l))
        question_match = answer_term_hits / len(intent_terms)
    else:
        question_match = 0.5
    if subjects:
        answer_subject_hits = 0
        for marker in subjects:
            pattern = next(p for name, p in _SUBJECT_PATTERNS if name == marker)
            if pattern.search(answer or ""):
                answer_subject_hits += 1
        question_match = min(
            question_match,
            answer_subject_hits / max(1, len(subjects)),
        )

    # Concept coverage: known enterprise concepts from the question.
    concepts = extract_question_concepts(question)
    if concepts:
        concept_hits = sum(1 for concept in concepts if contains_concept(enriched, concept))
        concept_coverage = concept_hits / len(concepts)
        reasons.append(f"concept_hits={concept_hits}/{len(concepts)}")
    else:
        concept_coverage = None

    # Blend: subjects dominate when present; concepts stabilize foundation questions.
    if subjects:
        intent_coverage = 0.7 * subject_coverage + 0.3 * term_coverage
    elif concept_coverage is not None:
        intent_coverage = (
            0.50 * concept_coverage + 0.30 * term_coverage + 0.20 * specificity
        )
    else:
        intent_coverage = 0.65 * term_coverage + 0.35 * specificity

    # Policy/procedure questions with a missing subject are uncovered.
    asks_policy = bool(
        re.search(r"\b(policy|procedure|guideline|standard)\b", question or "", re.I)
    )
    if asks_policy and subjects and subject_coverage < 1.0:
        intent_coverage = min(intent_coverage, 0.15)
        reasons.append("policy_subject_absent")

    intent_covered = intent_coverage >= 0.40 and (
        not subjects or subject_coverage >= 1.0
    )
    # Concepts fully present in evidence is a strong positive even with sparse terms.
    if (
        concept_coverage is not None
        and concept_coverage >= 0.99
        and not subjects
        and not (asks_policy and subjects)
    ):
        intent_covered = True
        intent_coverage = max(intent_coverage, 0.70)

    refusal = is_explicit_refusal(answer)
    multi_doc = has_multi_document_enumeration(answer)
    if multi_doc:
        reasons.append("multi_document_enumeration")
    if refusal:
        reasons.append("explicit_refusal")

    return IntentAssessment(
        intent_terms=tuple(intent_terms[:24]),
        subject_markers=tuple(subjects),
        intent_coverage=round(intent_coverage, 4),
        evidence_specificity=round(specificity, 4),
        question_match=round(question_match, 4),
        intent_covered=intent_covered,
        explicit_refusal=refusal,
        multi_document_enumeration=multi_doc,
        reasons=tuple(reasons),
    )
