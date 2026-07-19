"""Dynamic, AI-powered suggested questions for the chat empty state.

Replaces static example prompts with contextual questions mined from the
documents that are actually indexed and searchable right now.

Caching model
--------------
Mining headings (and optionally calling the LLM) is the expensive part, so
it only happens once per corpus version: the resulting candidate pool is
cached in memory on ``SuggestedQuestionService`` and reused for every
request until something invalidates it. The service subscribes to the same
in-process document lifecycle event bus that ``DocumentService`` already
publishes to (see ``app.documents.dispatcher``), so the cache is cleared
exactly when the corpus actually changes:

* a document finishes indexing (``DocumentIndexed``)
* a document is deleted (``DocumentDeleted``)
* a document is reindexed (``DocumentReindexed``)

A plain page refresh never touches the vector store or the LLM — it just
reads whatever is already cached.

RBAC
----
The candidate pool is mined from *every* indexed chunk, regardless of who
asks — exactly like the shared FAISS/BM25 index that chat retrieval already
searches over. Safety comes from filtering at serve time: callers pass the
authorized source-filename set (computed via the same
``RetrievalAuthorizationService`` used for chat answers) into
``get_suggestions``, and only candidates from those sources are ever
returned. No unauthorized document title, heading, or generated question
ever leaves this module.
"""

from __future__ import annotations

import logging
import re
import threading
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from app.core.logging import get_logger, log_with_fields
from app.ingestion.semantic_chunking.types import ChunkMetadata

if TYPE_CHECKING:
    from app.documents.events import DocumentLifecycleEvent
    from app.ingestion.chunker import DocumentChunk
    from app.ingestion.vector_store.base import VectorStore
    from app.llm.base import LLMProvider

logger = get_logger(__name__)

# Mining bounds — keep the cache-rebuild step (and any LLM call within it)
# fast and bounded regardless of corpus size.
MAX_DOCUMENTS_CONSIDERED = 12
MAX_HEADINGS_PER_DOCUMENT = 6
QUESTIONS_PER_DOCUMENT = 2
MAX_POOL_SIZE = 30
DEFAULT_SUGGESTION_LIMIT = 3

_MIN_HEADING_WORDS = 2
_MAX_HEADING_WORDS = 16
_MIN_QUESTION_WORDS = 3
_MAX_QUESTION_WORDS = 20

# Lifecycle operations that mean "the searchable corpus changed" — see
# app.documents.events for the full event catalogue.
_INVALIDATING_OPERATIONS = frozenset({"indexed", "deleted", "reindexed"})

# Generic, purely structural headings that make poor standalone questions.
# Deliberately domain-agnostic so this generalizes to any future corpus.
_GENERIC_HEADING_DENYLIST = frozenset(
    {
        "introduction",
        "overview",
        "contents",
        "table of contents",
        "appendix",
        "appendices",
        "conclusion",
        "conclusions",
        "references",
        "glossary",
        "acknowledgments",
        "acknowledgements",
        "revision history",
        "document control",
        "disclaimer",
        "disclosure",
    }
)

_ARTICLE_PREFIXES = ("the ", "a ", "an ")

_WORD_RE = re.compile(r"[A-Za-z0-9']+")

# Generic onboarding prompts shown when no authorized, indexed documents
# exist yet — never cached, since they never depend on corpus state.
ONBOARDING_QUESTIONS: tuple[str, ...] = (
    "What can this assistant help me with?",
    "How do I upload a document for the assistant to use?",
    "What kinds of questions can I ask once documents are added?",
)


@dataclass(frozen=True)
class SuggestedQuestion:
    """A single suggested question, tied back to the document that inspired it.

    ``source`` is the filename of the document this question was derived
    from — the same identifier used everywhere else for RBAC filtering. It
    is an empty string for generic onboarding prompts, which are not tied
    to any document.
    """

    text: str
    source: str
    document_title: str


@dataclass
class _DocumentProfile:
    """Headings mined for one indexed document, used to seed suggestions."""

    source: str
    document_title: str
    headings: list[str]


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _is_generic_heading(heading: str) -> bool:
    return heading.strip().lower().strip(":.") in _GENERIC_HEADING_DENYLIST


def _extract_chunks(vector_store: "VectorStore") -> list["DocumentChunk"]:
    """Return indexed chunks regardless of whether *vector_store* is a plain
    ``FaissVectorStore`` or a ``HybridIndexStore`` wrapping one."""
    faiss_store = getattr(vector_store, "faiss_store", vector_store)
    return list(getattr(faiss_store, "chunks", []))


def _collect_document_profiles(
    chunks: list["DocumentChunk"],
    *,
    max_documents: int = MAX_DOCUMENTS_CONSIDERED,
    max_headings_per_document: int = MAX_HEADINGS_PER_DOCUMENT,
) -> list[_DocumentProfile]:
    """Group indexed chunks by source document and extract usable headings.

    Only documents with at least one usable heading are returned. When more
    documents qualify than *max_documents*, the most recently indexed ones
    win (chunks are appended to the vector store in indexing order).
    """
    order: list[str] = []
    titles: dict[str, str] = {}
    headings_by_source: dict[str, list[str]] = defaultdict(list)
    seen_headings: dict[str, set[str]] = defaultdict(set)

    for chunk in chunks:
        source = chunk.source
        if source not in titles:
            order.append(source)
        metadata = chunk.metadata if isinstance(chunk.metadata, ChunkMetadata) else None
        titles.setdefault(source, (metadata.document_title if metadata else None) or source)

        if metadata is None or not metadata.section_title:
            continue
        heading = metadata.section_title.strip()
        if not heading or _is_generic_heading(heading):
            continue
        words = _word_count(heading)
        if words < _MIN_HEADING_WORDS or words > _MAX_HEADING_WORDS:
            continue

        key = heading.lower()
        if key in seen_headings[source]:
            continue
        if len(headings_by_source[source]) >= max_headings_per_document:
            continue
        seen_headings[source].add(key)
        headings_by_source[source].append(heading)

    profiles = [
        _DocumentProfile(
            source=source,
            document_title=titles[source],
            headings=headings_by_source.get(source, []),
        )
        for source in order
        if headings_by_source.get(source)
    ]
    if len(profiles) > max_documents:
        profiles = profiles[-max_documents:]
    return profiles


def _to_sentence_case(text: str) -> str:
    """Lower-case plain Title-Case words while preserving likely acronyms.

    Mirrors (in reverse) the acronym-preserving heuristic used for
    conversation titles: a word that contains a digit or has an uppercase
    letter after its first position (e.g. "FY2026", "KYC") is left alone;
    plain Title-Case words (e.g. "Commercial") are lower-cased so the
    heading reads naturally mid-sentence.
    """
    words = text.split()
    result = []
    for word in words:
        if any(char.isdigit() for char in word) or any(char.isupper() for char in word[1:]):
            result.append(word)
        else:
            result.append(word[:1].lower() + word[1:])
    return " ".join(result)


def _heading_to_question(heading: str, document_title: str) -> str:
    """Turn a heading into a natural question or prompt.

    Headings that are already phrased as questions (common in FAQ-style
    documents) are used verbatim — they are guaranteed relevant and well
    formed. Otherwise a short, domain-agnostic template is applied.
    """
    stripped = heading.strip().rstrip(".:")
    if not stripped:
        return f"What does {document_title} cover?"
    if stripped.endswith("?"):
        return stripped

    lowered = _to_sentence_case(stripped)
    if len(stripped.split()) <= 5:
        prefix = "" if lowered.startswith(_ARTICLE_PREFIXES) else "the "
        return f"Explain {prefix}{lowered}."
    return f"What does the {document_title} document say about {lowered}?"


def _deterministic_questions_for_profile(
    profile: _DocumentProfile,
    *,
    limit: int,
) -> list[SuggestedQuestion]:
    questions: list[SuggestedQuestion] = []
    for heading in profile.headings:
        if len(questions) >= limit:
            break
        text = _heading_to_question(heading, profile.document_title)
        questions.append(
            SuggestedQuestion(
                text=text,
                source=profile.source,
                document_title=profile.document_title,
            )
        )
    return questions


_QUESTION_SYSTEM_PROMPT_TEMPLATE = (
    "You generate short, natural questions for an enterprise knowledge "
    "assistant's suggested-questions panel. You will be given a numbered "
    "list of documents, each with a title and a few section headings taken "
    "directly from that document. For each document, write up to {per_document} "
    "short question(s) or request(s) (4-14 words each) that a curious "
    "employee might ask about it, grounded ONLY in the given title and "
    "headings — never invent facts, numbers, or names that are not implied "
    "by them.\n\n"
    "Respond with exactly one line per question, in this exact format:\n"
    "<document number> | <question text>\n\n"
    "Rules:\n"
    "- No numbering inside the question text, no bullets, no quotes.\n"
    '- Mix interrogative ("What...", "How...") and imperative '
    '("Explain...") phrasing.\n'
    "- Do not add any other text, headers, or explanations."
)


def _build_llm_prompt_user_content(profiles: list[_DocumentProfile]) -> str:
    lines: list[str] = []
    for position, profile in enumerate(profiles, start=1):
        headings = ", ".join(profile.headings) if profile.headings else "(none)"
        lines.append(f"{position}. Title: {profile.document_title}\n   Headings: {headings}")
    return "\n\n".join(lines)


def _parse_llm_question_lines(
    raw: str,
    *,
    num_documents: int,
    per_document: int,
) -> dict[int, list[str]]:
    """Parse ``"<n> | <question>"`` lines into ``{document_position: [texts]}``.

    Malformed lines, out-of-range indices, and implausibly short/long
    "questions" are silently skipped — a partially unparsable response
    still yields whatever usable lines it contains.
    """
    result: dict[int, list[str]] = defaultdict(list)
    for raw_line in raw.splitlines():
        line = raw_line.strip().lstrip("-*• ").strip()
        if not line or "|" not in line:
            continue
        index_part, _, question_part = line.partition("|")
        question = question_part.strip().strip("\"'")
        if not question:
            continue
        try:
            index = int(index_part.strip())
        except ValueError:
            continue
        if not (1 <= index <= num_documents):
            continue
        words = _word_count(question)
        if words < _MIN_QUESTION_WORDS or words > _MAX_QUESTION_WORDS:
            continue
        if len(result[index]) >= per_document:
            continue
        result[index].append(question)
    return result


def _try_llm_questions(
    profiles: list[_DocumentProfile],
    llm_provider: "LLMProvider",
    *,
    per_document: int,
) -> dict[int, list[str]]:
    """Attempt LLM-based question generation for *profiles*.

    Returns an empty dict on any failure at all — callers always have the
    deterministic per-document fallback available. Never raises.
    """
    from app.llm.exceptions import LLMError
    from app.llm.types import BuiltPrompt, LLMGenerationRequest

    system_prompt = _QUESTION_SYSTEM_PROMPT_TEMPLATE.format(per_document=per_document)
    user_content = _build_llm_prompt_user_content(profiles)
    prompt = BuiltPrompt(
        system=system_prompt,
        user=user_content,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    request = LLMGenerationRequest(
        question=user_content,
        retrieved_chunks=[],
        conversation_history=None,
        prompt=prompt,
    )

    try:
        result = llm_provider.generate_sync(request)
    except LLMError as exc:
        log_with_fields(
            logger,
            logging.WARNING,
            "Suggested question LLM call failed; using deterministic fallback",
            reason=type(exc).__name__,
        )
        return {}
    except Exception as exc:  # defensive: must never break the request path
        log_with_fields(
            logger,
            logging.WARNING,
            "Suggested question LLM call raised an unexpected error; using deterministic fallback",
            reason=type(exc).__name__,
        )
        return {}

    if not result.answer or not result.answer.strip():
        return {}
    return _parse_llm_question_lines(
        result.answer,
        num_documents=len(profiles),
        per_document=per_document,
    )


def _build_pool(
    chunks: list["DocumentChunk"],
    llm_provider: "LLMProvider | None",
) -> list[SuggestedQuestion]:
    """Mine a candidate suggestion pool from currently indexed *chunks*.

    Grounded entirely in real document headings/titles. The LLM step (when a
    provider is configured) makes a single bounded call covering every
    profile at once — never one call per document — so cache-rebuild latency
    stays bounded regardless of corpus size. Any document the LLM does not
    produce a usable line for simply falls back to the deterministic
    heading-templated question for that document.
    """
    profiles = _collect_document_profiles(chunks)
    if not profiles:
        return []

    llm_questions: dict[int, list[str]] = {}
    if llm_provider is not None:
        try:
            llm_questions = _try_llm_questions(
                profiles, llm_provider, per_document=QUESTIONS_PER_DOCUMENT
            )
        except Exception as exc:  # defensive: mining must never raise
            log_with_fields(
                logger,
                logging.WARNING,
                "Suggested question LLM generation failed unexpectedly; "
                "using deterministic fallback for all documents",
                reason=type(exc).__name__,
            )
            llm_questions = {}

    pool: list[SuggestedQuestion] = []
    for position, profile in enumerate(profiles, start=1):
        texts = llm_questions.get(position)
        if texts:
            questions = [
                SuggestedQuestion(
                    text=text,
                    source=profile.source,
                    document_title=profile.document_title,
                )
                for text in texts
            ]
        else:
            questions = _deterministic_questions_for_profile(
                profile, limit=QUESTIONS_PER_DOCUMENT
            )
        pool.extend(questions)

    return pool[:MAX_POOL_SIZE]


def _diversify(pool: list[SuggestedQuestion], *, limit: int) -> list[SuggestedQuestion]:
    """Prefer one question per distinct source before repeating any document."""
    seen_sources: set[str] = set()
    first_pass: list[SuggestedQuestion] = []
    remainder: list[SuggestedQuestion] = []
    for question in pool:
        if question.source not in seen_sources:
            first_pass.append(question)
            seen_sources.add(question.source)
        else:
            remainder.append(question)
    return (first_pass + remainder)[:limit]


def _onboarding_suggestions(limit: int) -> list[SuggestedQuestion]:
    return [
        SuggestedQuestion(text=text, source="", document_title="")
        for text in ONBOARDING_QUESTIONS[:limit]
    ]


class SuggestedQuestionService:
    """Cache and serve contextual suggested questions mined from indexed documents.

    See the module docstring for the full caching and RBAC design.
    """

    def __init__(
        self,
        vector_store: "VectorStore",
        llm_provider: "LLMProvider | None" = None,
    ) -> None:
        self._vector_store = vector_store
        self._llm_provider = llm_provider
        self._lock = threading.Lock()
        self._pool: list[SuggestedQuestion] | None = None

    def invalidate(self) -> None:
        """Clear the cached candidate pool so it is rebuilt on next access."""
        with self._lock:
            self._pool = None

    def on_lifecycle_event(self, event: "DocumentLifecycleEvent") -> None:
        """Invalidate the cache when the searchable corpus actually changes.

        Registered as a handler on the shared document lifecycle event
        collector (see ``get_suggested_question_service``). Ignores events
        that do not change what is currently searchable (e.g. an upload
        that has not finished indexing yet, or a processing-failed event).
        """
        if event.operation in _INVALIDATING_OPERATIONS:
            self.invalidate()

    def get_candidate_pool(self) -> list[SuggestedQuestion]:
        """Return the cached candidate pool, mining it on first access."""
        if self._pool is not None:
            return self._pool
        with self._lock:
            if self._pool is None:
                chunks = _extract_chunks(self._vector_store)
                try:
                    pool = _build_pool(chunks, self._llm_provider)
                except Exception as exc:  # defensive: never break the request path
                    log_with_fields(
                        logger,
                        logging.WARNING,
                        "Suggested question mining failed; falling back to onboarding questions",
                        reason=type(exc).__name__,
                    )
                    pool = []
                self._pool = pool
                log_with_fields(
                    logger,
                    logging.INFO,
                    "Suggested question candidate pool rebuilt",
                    pool_size=len(pool),
                    chunks_scanned=len(chunks),
                )
        return self._pool

    def get_suggestions(
        self,
        authorized_sources: frozenset[str] | None,
        *,
        limit: int = DEFAULT_SUGGESTION_LIMIT,
    ) -> list[SuggestedQuestion]:
        """Return up to *limit* suggestions the caller is authorized to see.

        Args:
            authorized_sources: Filenames the requesting user may read.
                ``None`` skips RBAC filtering entirely — only safe for
                internal/test callers; real requests must always pass a
                computed set (an empty ``frozenset()`` when nothing is
                authorized).
            limit: Maximum number of suggestions to return.

        Returns:
            Up to *limit* document-grounded suggestions, diversified across
            source documents. Falls back to generic onboarding questions
            when the pool is empty or nothing in it is authorized.
        """
        pool = self.get_candidate_pool()
        if authorized_sources is not None:
            pool = [question for question in pool if question.source in authorized_sources]

        selected = _diversify(pool, limit=limit)
        if not selected:
            return _onboarding_suggestions(limit)
        return selected


@lru_cache
def get_suggested_question_service() -> SuggestedQuestionService:
    """Return the cached suggested-question service, wired to lifecycle events.

    Subscribes to the document service's shared lifecycle event collector so
    the candidate pool is invalidated exactly when the corpus changes
    (upload finishes indexing, a document is deleted, or a reindex happens)
    — never on a plain page refresh.
    """
    from app.services.document_service import get_document_service
    from app.services.title_generation import get_title_llm_provider

    document_service = get_document_service()
    service = SuggestedQuestionService(
        document_service.vector_store,
        # Reuses the same short-timeout provider built for title generation:
        # both are small, latency-sensitive LLM calls that must never stall
        # an otherwise-successful request when a provider is slow/down.
        llm_provider=get_title_llm_provider(),
    )
    document_service.event_collector.subscribe(service.on_lifecycle_event)
    return service
