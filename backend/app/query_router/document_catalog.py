"""Build tenant-agnostic routing signals from authorized uploaded documents.

Uses filenames / stems already available at ask-time ACL resolution.
Never hardcodes organization-specific document names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_EXT_RE = re.compile(r"\.(md|pdf|docx?|txt|html?)$", re.I)
_LEADING_INDEX_RE = re.compile(r"^\d+[_\-\s]+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_DOC_ID_RE = re.compile(
    r"\b[A-Z]{2,}(?:-[A-Z0-9]{2,}){1,3}-\d{2,}\b"
)

# Tokens too generic to count as a document-title hit on their own.
_STOP_TOKENS = frozenset(
    {
        "a",
        "an",
        "and",
        "the",
        "of",
        "for",
        "to",
        "in",
        "on",
        "by",
        "with",
        "from",
        "or",
        "is",
        "are",
        "what",
        "how",
        "when",
        "where",
        "who",
        "why",
        "this",
        "that",
        "our",
        "my",
        "your",
        "document",
        "documents",
        "file",
        "files",
        "pdf",
        "doc",
        "docx",
        "md",
        "txt",
        "v1",
        "v2",
        "v3",
        "v4",
        "final",
        "draft",
        "copy",
        "new",
        "old",
        "case",
        "001",
        "002",
        "003",
    }
)


@dataclass(frozen=True)
class DocumentRouteCatalog:
    """Per-request catalog derived from the caller's authorized sources."""

    filenames: tuple[str, ...] = ()
    titles: tuple[str, ...] = ()
    tokens: frozenset[str] = frozenset()
    document_ids: frozenset[str] = frozenset()

    @property
    def is_empty(self) -> bool:
        return not self.filenames and not self.titles


def humanize_filename(filename: str) -> str:
    """Convert a stored filename into a lightweight title-like phrase."""
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    name = _EXT_RE.sub("", name)
    name = _LEADING_INDEX_RE.sub("", name)
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name


def tokenize_title(text: str) -> set[str]:
    """Extract distinctive lowercase tokens from a title or query fragment."""
    lowered = text.lower()
    parts = [p for p in _NON_ALNUM_RE.split(lowered) if p]
    return {p for p in parts if len(p) >= 3 and p not in _STOP_TOKENS}


def extract_document_ids(text: str) -> set[str]:
    """Return format-agnostic document-style IDs found in *text*."""
    return {match.group(0).upper() for match in _DOC_ID_RE.finditer(text or "")}


def build_document_route_catalog(
    authorized_sources: frozenset[str] | set[str] | list[str] | None,
) -> DocumentRouteCatalog:
    """Build routing catalog from authorized document filenames."""
    if not authorized_sources:
        return DocumentRouteCatalog()

    filenames: list[str] = []
    titles: list[str] = []
    tokens: set[str] = set()
    document_ids: set[str] = set()

    for raw in sorted(authorized_sources):
        filename = str(raw).strip()
        if not filename:
            continue
        filenames.append(filename)
        title = humanize_filename(filename)
        if title:
            titles.append(title)
            tokens |= tokenize_title(title)
        document_ids |= extract_document_ids(filename)
        document_ids |= extract_document_ids(title)

    return DocumentRouteCatalog(
        filenames=tuple(filenames),
        titles=tuple(titles),
        tokens=frozenset(tokens),
        document_ids=frozenset(document_ids),
    )


def score_catalog_overlap(query: str, catalog: DocumentRouteCatalog) -> tuple[float, tuple[str, ...]]:
    """Score lexical overlap between the query and authorized document titles."""
    if catalog.is_empty:
        return 0.0, ()

    query_lower = query.lower()
    signals: list[str] = []
    score = 0.0

    for filename in catalog.filenames:
        stem = humanize_filename(filename).lower()
        if stem and stem in query_lower:
            signals.append("catalog_title_substring")
            score = max(score, 0.93)
            break
        bare = filename.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if bare and bare in query_lower:
            signals.append("catalog_filename_substring")
            score = max(score, 0.94)
            break

    query_ids = extract_document_ids(query)
    if query_ids and query_ids & catalog.document_ids:
        signals.append("catalog_document_id")
        score = max(score, 0.95)

    query_tokens = tokenize_title(query)
    if query_tokens and catalog.tokens:
        overlap = query_tokens & catalog.tokens
        if len(overlap) >= 2:
            signals.append("catalog_token_overlap")
            score = max(score, 0.86)
        elif len(overlap) == 1:
            # Single distinctive token (e.g. "taxonomy", "handbook") is still useful.
            token = next(iter(overlap))
            if len(token) >= 6:
                signals.append("catalog_token_hit")
                score = max(score, 0.78)

    return score, tuple(signals)
