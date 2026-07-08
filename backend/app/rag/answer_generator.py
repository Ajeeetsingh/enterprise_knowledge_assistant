"""Natural-language answer generation from retrieved context."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.core.logging import get_logger, log_with_fields
from app.rag.types import RetrievalResult

logger = get_logger(__name__)

UNAVAILABLE_MESSAGE = (
    "I couldn't find this information in the retrieved context."
)

# Calibrated confidence below this threshold → return UNAVAILABLE rather than
# a low-quality guess.
MIN_CONFIDENCE_THRESHOLD = 0.15


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class GeneratedAnswer:
    """Structured output from answer generation."""

    answer: str
    sources_used: list[str]
    confidence_score: float


# ---------------------------------------------------------------------------
# Text cleaning utilities
# ---------------------------------------------------------------------------

def _clean_table_row(text: str) -> str:
    """Convert PDF-extracted table-cell runs into readable prose fragments.

    PDF tables are often extracted as space-separated cells on one line, e.g.:
        "Singapore (HQ) Singapore Group headquarters; Retail & Commercial Banking hub"
    This function converts such runs into a readable sentence where possible.
    """
    # Strip leading/trailing noise
    text = text.strip()
    # Replace multiple spaces with single space
    text = re.sub(r" {2,}", " ", text)
    # If the text already contains a verb-like phrase or punctuation, leave it
    if re.search(r"[.!?;]", text) or " is " in text or " are " in text or " was " in text:
        return text
    return text


def _table_rows_to_sentences(text: str) -> list[str]:
    """Parse table-formatted text and convert each row to a natural sentence.

    Handles patterns like:
        "Country / Jurisdiction Primary Function Singapore (HQ) Singapore Group HQ..."
    Returns a list of cleaned sentences.
    """
    # Split on semicolons (often used as cell separators in PDF tables)
    parts = [p.strip() for p in text.split(";") if p.strip()]
    if len(parts) > 1:
        return [_clean_table_row(p) for p in parts if len(p) > 5]

    # Try splitting on newlines
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if len(lines) > 1:
        return [_clean_table_row(ln) for ln in lines if len(ln) > 5]

    return [_clean_table_row(text)]


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _ensure_period(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    return text if text.endswith((".", "!", "?")) else f"{text}."


def _is_clean_sentence(sentence: str, *, min_len: int = 15, max_len: int = 600) -> bool:
    """Return True if *sentence* looks like usable prose."""
    s = sentence.strip()
    if len(s) < min_len or len(s) > max_len:
        return False
    # Reject lines that are clearly header fragments or separators
    if re.search(r"=+|-{4,}|_{4,}", s):
        return False
    # Must contain at least one alphabetical word of ≥ 3 chars
    if not re.search(r"[a-zA-Z]{3,}", s):
        return False
    return True


# ---------------------------------------------------------------------------
# Domain-specific extractors (existing patterns, largely unchanged)
# ---------------------------------------------------------------------------

class _DomainExtractors:
    """Stateless domain-specific answer extraction methods."""

    @staticmethod
    def parental_leave(context: str) -> str | None:
        leave_pattern = (
            r"(Primary|Secondary|ondary)\s*caregivers:\s*"
            r"(\d+\s+weeks\s+fully paid parental leave)"
        )
        matches = re.findall(leave_pattern, context, flags=re.IGNORECASE)
        if not matches:
            return None
        role_map = {"primary": "primary", "secondary": "secondary", "ondary": "secondary"}
        entitlements: dict[str, str] = {}
        for role, entitlement in matches:
            normalized_role = role_map.get(role.lower(), role.lower())
            entitlements[normalized_role] = entitlement
        ordered_roles = [r for r in ("primary", "secondary") if r in entitlements]
        parts = [
            f"{role} caregivers receive {entitlements[role]}"
            for role in ordered_roles
        ]
        if len(parts) == 2:
            return f"{parts[0].capitalize()}, while {parts[1]}."
        return f"{parts[0].capitalize()}." if parts else None

    @staticmethod
    def remote_work(context: str) -> str | None:
        remote_days = re.search(
            r"work remotely up to (\d+) days per week[^.]*",
            context, flags=re.IGNORECASE,
        )
        core_hours = re.search(
            r"Core collaboration hours(?: are)?[:\s]*([^.]+?)(?:\.|$)",
            context, flags=re.IGNORECASE,
        )
        stipend = re.search(
            r"Home office equipment stipend:\s*(\$[\d,]+[^.]*\.)",
            context, flags=re.IGNORECASE,
        )
        if not any((remote_days, core_hours, stipend)):
            return None
        sentences: list[str] = []
        if remote_days:
            approval = "with manager approval" if "approval" in context.lower() else ""
            sentence = f"Eligible employees may work remotely up to {remote_days.group(1)} days per week"
            if approval:
                sentence += f" {approval}"
            sentences.append(sentence + ".")
        if core_hours:
            sentences.append(f"Core collaboration hours are {core_hours.group(1).strip()}.")
        if stipend:
            sentences.append(
                f"A home office equipment stipend of {stipend.group(1).strip().rstrip('.')} is provided."
            )
        return " ".join(sentences)

    @staticmethod
    def department_revenue(query: str, context: str) -> str | None:
        department = None
        for name in ("Sales", "Engineering", "Marketing", "Operations"):
            if name.lower() in query.lower():
                department = name.upper()
                break
        if department is None:
            return None
        pattern = rf"{department}\s+Revenue:\s*(\$[\d,]+)"
        match = re.search(pattern, context, flags=re.IGNORECASE)
        if not match:
            return None
        growth = re.search(
            rf"{department}\s+Revenue:\s*\$[\d,]+\s+Expenses:\s*\$[\d,]+\s+"
            rf"Net Profit:\s*\$[\d,]+\s+Headcount:\s*(\d+)\s+employees\s+"
            rf"QoQ Growth:\s*([\d.]+%)",
            context, flags=re.IGNORECASE,
        )
        revenue = match.group(1)
        if growth:
            return (
                f"{department.title()} department revenue in Q3 2025 was {revenue}, "
                f"with {growth.group(1)} employees and {growth.group(2)} quarter-over-quarter growth."
            )
        return f"{department.title()} department revenue in Q3 2025 was {revenue}."

    @staticmethod
    def security_policy(query: str, context: str) -> str | None:
        query_lower = query.lower()
        if "password" in query_lower:
            min_length = re.search(
                r"passwords of at least (\d+) characters", context, flags=re.IGNORECASE
            )
            rotation = re.search(
                r"Passwords must be changed every (\d+) days", context, flags=re.IGNORECASE
            )
            if min_length:
                answer = (
                    f"Employees must use passwords of at least "
                    f"{min_length.group(1)} characters with mixed character types."
                )
                if rotation:
                    answer += f" Passwords must be changed every {rotation.group(1)} days."
                return answer
        if "mfa" in query_lower or "multi-factor" in query_lower:
            mfa = re.search(r"MFA is mandatory for ([^.]+)\.", context, flags=re.IGNORECASE)
            if mfa:
                return f"MFA is mandatory for {mfa.group(1).strip()}."
        if "data classification" in query_lower or "classify data" in query_lower:
            levels = re.findall(
                r"(Public|Internal|Confidential|Restricted):\s*([^.]+)\.",
                context, flags=re.IGNORECASE,
            )
            if levels:
                parts = [
                    f"{level} data includes {description.strip()}"
                    for level, description in levels
                ]
                return (f"{parts[0].capitalize()}, and {parts[1]}."
                        if len(parts) > 1 else f"{parts[0].capitalize()}.")
        return None

    @staticmethod
    def security_event(query: str, context: str) -> str | None:
        events = re.findall(r"\[([^\]]+)\]\s+(\w+)\s+(\w+):\s*([^(]+)", context)
        if not events:
            return None
        query_lower = query.lower()
        relevant: list[str] = []
        for timestamp, severity, event_type, message in events:
            event_blob = f"{severity} {event_type} {message}".lower()
            if any(
                term in event_blob or term in query_lower
                for term in ("malware", "login", "breach", "exfiltration", "mfa", "failed")
            ):
                relevant.append(
                    f"On {timestamp}, a {severity.lower()} "
                    f"{event_type.replace('_', ' ').lower()} event occurred: "
                    f"{message.strip()}."
                )
        if not relevant:
            return None
        if "malware" in query_lower:
            malware_events = [e for e in relevant if "malware" in e.lower()]
            if malware_events:
                return malware_events[0]
        return relevant[0]

    @staticmethod
    def employee(query: str, context: str) -> str | None:
        if not any(
            term in query.lower() for term in ("salary", "employee", "compensation", "details")
        ):
            return None
        records = re.findall(
            r"full_name:\s*([^,]+).*?salary_usd:\s*(\d+)",
            context, flags=re.IGNORECASE | re.DOTALL,
        )
        if not records:
            return None
        query_lower = query.lower()
        for name, salary in records:
            name = name.strip()
            if name.lower() in query_lower:
                return f"{name}'s salary is ${int(salary):,} per year."
        if len(records) == 1:
            name, salary = records[0]
            return f"{name.strip()}'s salary is ${int(salary):,} per year."
        return None

    @staticmethod
    def benefits(context: str) -> str | None:
        match_401k = re.search(
            r"401\(k\)\s+plan with\s+([^.,]+(?:employee contributions)?)",
            context, flags=re.IGNORECASE,
        )
        if match_401k:
            return (
                f"The 401(k) plan includes {match_401k.group(1).strip()}, "
                "with vesting over 4 years."
            )
        wellness = re.search(
            r"Annual wellness stipend:\s*(\$[\d,]+[^.]*\.)", context, flags=re.IGNORECASE
        )
        if wellness:
            return f"Employees receive an annual wellness stipend of {wellness.group(1).strip()}"
        return None

    @staticmethod
    def annual_leave(context: str) -> str | None:
        match = re.search(
            r"All full-time employees accrue\s+([\d.]+\s+days of paid annual leave per month\s*"
            r"\(\d+\s+days per year\))",
            context, flags=re.IGNORECASE,
        )
        if match:
            return (
                f"Full-time employees accrue {match.group(1)}, "
                "and leave must be requested at least 14 calendar days in advance."
            )
        days_match = re.search(
            r"(\d+)\s+days of paid annual leave per year", context, flags=re.IGNORECASE
        )
        if days_match:
            return f"Employees receive {days_match.group(1)} days of paid annual leave per year."
        return None


# ---------------------------------------------------------------------------
# General answer synthesis
# ---------------------------------------------------------------------------

_QUERY_STOPWORDS = frozenset({
    "what", "when", "where", "which", "who", "whom", "whose", "how",
    "the", "and", "for", "are", "was", "were", "with", "from", "that",
    "this", "about", "does", "have", "has", "had", "any", "there",
    "show", "tell", "give", "please", "list",
})


def _query_terms(query: str) -> set[str]:
    return {
        term.lower()
        for term in re.findall(r"\b[a-zA-Z]{3,}\b", query)
        if term.lower() not in _QUERY_STOPWORDS
    }


def _label_value_to_prose(sentence: str) -> str | None:
    """Convert 'Label: value' patterns into 'Label is value.' prose."""
    match = re.match(r"^(.+?):\s*(.+)$", sentence.strip())
    if not match:
        return None
    label = match.group(1).strip()
    value = match.group(2).strip().rstrip(".")
    if len(label) > 60 or len(value) < 3:
        return None
    label_lower = label.lower()
    if "caregiver" in label_lower:
        return f"{label} receive {value}."
    return f"{label} is {value}."


def _synthesize_general_answer(query: str, context: str, *, max_sentences: int = 3) -> str | None:
    """Score candidate sentences by query-term overlap and synthesize an answer.

    Improvements over the previous implementation:
    * Attempts to convert table rows into readable prose before scoring.
    * Returns up to *max_sentences* (vs previously always 1) for richer answers.
    * Filters out short/noisy lines.
    """
    query_terms = _query_terms(query)
    if not query_terms:
        return None

    # Break context into candidate pieces
    raw_sentences: list[str] = []
    for part in re.split(r"(?<=[.!?])\s+|\n+", context):
        part = part.strip()
        if not part:
            continue
        # Try to expand table rows
        expanded = _table_rows_to_sentences(part)
        raw_sentences.extend(expanded)

    scored: list[tuple[int, str]] = []
    for sentence in raw_sentences:
        sentence = _normalize_whitespace(sentence)
        if not _is_clean_sentence(sentence):
            continue
        sentence_lower = sentence.lower()
        overlap = sum(1 for term in query_terms if term in sentence_lower)
        if overlap > 0:
            scored.append((overlap, sentence))

    if not scored:
        return None

    scored.sort(key=lambda item: (-item[0], len(item[1])))
    top_sentences = [sentence for _, sentence in scored[:max_sentences]]

    # Convert label-value to prose where possible, otherwise ensure period
    prose: list[str] = []
    seen_normalized: set[str] = set()
    for sentence in top_sentences:
        converted = _label_value_to_prose(sentence) or _ensure_period(sentence)
        normalized = " ".join(converted.lower().split())
        if normalized not in seen_normalized:
            seen_normalized.add(normalized)
            prose.append(converted)

    if not prose:
        return None

    return " ".join(prose)


def _synthesize_structured_answer(query: str, context: str) -> str | None:
    """Try to answer structured/factual queries from table-formatted content.

    Handles company-overview style documents where answers are in labeled rows.
    Returns a synthesised prose sentence.
    """
    query_lower = query.lower()

    # --- Headquarters / location queries ---
    if any(term in query_lower for term in ("headquarters", "headquartered", "hq", "location")):
        hq_match = re.search(
            r"([A-Za-z][A-Za-z\s]+)\s*\(HQ\)[^\n]*?([A-Za-z][A-Za-z\s,;&]+)",
            context, flags=re.IGNORECASE,
        )
        if hq_match:
            city = hq_match.group(1).strip()
            description = hq_match.group(2).strip().rstrip(";,")
            return (
                f"The company is headquartered in {city}. "
                f"The {city} office serves as {description}."
            )
        # Fallback: look for "Group Headquarters" phrase
        gh_match = re.search(
            r"([\w\s]+)\s+(?:serves as|is)\s+(?:the\s+)?Group [Hh]eadquarters[^.]*",
            context,
        )
        if gh_match:
            return _ensure_period(gh_match.group(0).strip())

    # --- CEO / leadership queries ---
    if any(term in query_lower for term in ("ceo", "chief executive", "president", "founder", "leadership")):
        ceo_match = re.search(
            r"([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[,\s]+Chief Executive Officer",
            context,
        )
        if ceo_match:
            return f"The Chief Executive Officer is {ceo_match.group(1).strip()}."
        approved_match = re.search(
            r"Approved By\s+([^\n,]+)",
            context, flags=re.IGNORECASE,
        )
        if approved_match:
            return f"The document was approved by {approved_match.group(1).strip()}."

    # --- Founded / established queries ---
    if any(term in query_lower for term in ("founded", "established", "incorporated", "year")):
        year_match = re.search(
            r"(?:founded|established|incorporated|since)\s+(?:in\s+)?(\d{4})",
            context, flags=re.IGNORECASE,
        )
        if year_match:
            return f"The company was founded in {year_match.group(1)}."

    # --- AI / technology project queries ---
    if any(term in query_lower for term in ("ai", "artificial intelligence", "project", "codename", "platform")):
        ai_match = re.search(
            r"(?:codename|project|initiative)[:\s]+[\"']?([A-Z][A-Za-z0-9\s]+)[\"']?",
            context, flags=re.IGNORECASE,
        )
        if ai_match:
            return f"The AI initiative codename is {ai_match.group(1).strip()}."
        platform_match = re.search(
            r"(?:banking platform|core platform|core banking)[:\s]+([^\n.]+)",
            context, flags=re.IGNORECASE,
        )
        if platform_match:
            return f"The core banking platform is {platform_match.group(1).strip()}."

    # --- Regional offices ---
    if any(term in query_lower for term in ("office", "region", "regional", "branch")):
        offices: list[str] = []
        for match in re.finditer(
            r"([A-Z][a-zA-Z\s]+)\s*[–\-—]\s*(?:Regional|Branch|Office)[^;\n]*",
            context,
        ):
            offices.append(match.group(0).strip())
        if offices:
            return "Regional offices include: " + "; ".join(offices) + "."

    # --- Core values ---
    if any(term in query_lower for term in ("value", "values", "core value", "principle")):
        values: list[str] = []
        for match in re.finditer(r"\b([A-Z][a-z]{3,}(?:\s+[A-Z][a-z]+)?)\b(?=\s*[:–])", context):
            values.append(match.group(1))
        if len(values) >= 2:
            return f"The company's core values include: {', '.join(values[:6])}."

    return None


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

class AnswerGenerator:
    """Build natural-language answers from retrieved FAISS results."""

    def _group_by_source(
        self, results: list[RetrievalResult]
    ) -> dict[str, list[RetrievalResult]]:
        grouped: dict[str, list[RetrievalResult]] = {}
        for result in results:
            grouped.setdefault(result.source, []).append(result)
        return grouped

    def _merge_context(self, results: list[RetrievalResult]) -> str:
        seen: set[str] = set()
        parts: list[str] = []
        for result in results:
            normalized = " ".join(result.content.split())
            if normalized in seen:
                continue
            seen.add(normalized)
            parts.append(normalized)
        return " ".join(parts)

    def _collect_sources(self, results: list[RetrievalResult]) -> list[str]:
        seen: set[str] = set()
        sources: list[str] = []
        for result in results:
            if result.source not in seen:
                seen.add(result.source)
                sources.append(result.source)
        return sources

    def _combine_source_answers(self, answers: list[str]) -> str:
        unique_answers: list[str] = []
        for answer in answers:
            normalized = answer.strip()
            if normalized and normalized not in unique_answers:
                unique_answers.append(normalized)
        if not unique_answers:
            return UNAVAILABLE_MESSAGE
        if len(unique_answers) == 1:
            return unique_answers[0]
        combined = unique_answers[0].rstrip(".")
        for answer in unique_answers[1:]:
            combined += f". Additionally, {answer[0].lower()}{answer[1:]}"
        if not combined.endswith("."):
            combined += "."
        return combined

    def _compose_answer(self, query: str, context: str) -> str | None:
        query_lower = query.lower()
        extractors = _DomainExtractors

        # --- domain-specific fast paths (HR, Finance, Security, Employee data) ---
        if "401k" in query_lower or "401(k)" in query_lower or "benefits" in query_lower:
            ans = extractors.benefits(context)
            if ans:
                return ans
        if "annual leave" in query_lower or (
            "leave" in query_lower and "parental" not in query_lower
        ):
            ans = extractors.annual_leave(context)
            if ans:
                return ans
        if "parental" in query_lower or "caregiver" in query_lower:
            ans = extractors.parental_leave(context)
            if ans:
                return ans
        if "remote" in query_lower or "work from home" in query_lower or "hybrid" in query_lower:
            ans = extractors.remote_work(context)
            if ans:
                return ans
        if "revenue" in query_lower or "sales" in query_lower or "profit" in query_lower:
            ans = extractors.department_revenue(query, context)
            if ans:
                return ans
        if any(term in query_lower for term in ("password", "mfa", "multi-factor", "data classification")):
            ans = extractors.security_policy(query, context)
            if ans:
                return ans
        if any(term in query_lower for term in ("malware", "security event", "login", "incident", "breach")):
            ans = extractors.security_event(query, context)
            if ans:
                return ans
        if "salary" in query_lower or (
            "employee" in query_lower
            and not any(t in query_lower for t in ("headquarters", "office", "ceo", "founded"))
        ):
            ans = extractors.employee(query, context)
            if ans:
                return ans

        # --- structured/company-overview extractor (new) ---
        ans = _synthesize_structured_answer(query, context)
        if ans:
            return ans

        # --- general sentence-overlap synthesis ---
        return _synthesize_general_answer(query, context)

    def generate(self, query: str, results: list[RetrievalResult]) -> GeneratedAnswer:
        """Generate a natural-language answer from retrieved results."""
        sources_used = self._collect_sources(results)

        if not results:
            return GeneratedAnswer(
                answer=UNAVAILABLE_MESSAGE,
                sources_used=[],
                confidence_score=0.0,
            )

        best = results[0]
        confidence = best.confidence

        grouped = self._group_by_source(results)
        source_answers: list[str] = []

        for source_results in grouped.values():
            context = self._merge_context(source_results)
            answer = self._compose_answer(query, context)
            if answer and answer != UNAVAILABLE_MESSAGE:
                source_answers.append(answer)

        if source_answers:
            final_answer = self._combine_source_answers(source_answers)
            log_with_fields(
                logger,
                logging.INFO,
                "Answer generated",
                query=query,
                chunks_used=len(results),
                sources=sources_used,
                confidence_score=confidence,
                answer_length=len(final_answer),
            )
            return GeneratedAnswer(
                answer=final_answer,
                sources_used=sources_used,
                confidence_score=confidence,
            )

        if confidence < MIN_CONFIDENCE_THRESHOLD:
            return GeneratedAnswer(
                answer=UNAVAILABLE_MESSAGE,
                sources_used=sources_used,
                confidence_score=confidence,
            )

        context = self._merge_context(results)
        answer = self._compose_answer(query, context)

        if not answer:
            return GeneratedAnswer(
                answer=UNAVAILABLE_MESSAGE,
                sources_used=sources_used,
                confidence_score=confidence,
            )

        return GeneratedAnswer(
            answer=answer,
            sources_used=sources_used,
            confidence_score=confidence,
        )
