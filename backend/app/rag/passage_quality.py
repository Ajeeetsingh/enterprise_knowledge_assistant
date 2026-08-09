"""Shared passage-quality checks used after retrieval (merge / rerank blend)."""

from __future__ import annotations

import re

_MASTHEAD_RE = re.compile(
    r"enterprise governance\s+"
    r"(?:policy|standard|guide|reference|matrix|document)",
    re.IGNORECASE,
)


def is_low_information_stub(content: str | None) -> bool:
    """True for cover/title/heading-only fragments with no answer-bearing prose."""
    text = " ".join((content or "").split())
    if not text:
        return True
    return len(text) <= 48 and len(text.split()) <= 6


def is_document_masthead(content: str | None) -> bool:
    """True for short document title/banner pages (org name + governance tagline).

    Mission/vision regression: after cover stubs were removed, CE still ranked
    these banners above Mission/Vision/Core Values body chunks and filled
    context_top_k with them.
    """
    text = " ".join((content or "").split())
    if not text:
        return False
    if len(text.split()) > 45:
        return False
    return _MASTHEAD_RE.search(text) is not None


def should_skip_merge_candidate(content: str | None) -> bool:
    """Skip passages that must not consume multi-query merge slots."""
    return is_low_information_stub(content) or is_document_masthead(content)


def low_information_stub_penalty(content: str | None) -> float:
    """Return [0, 1] penalty for cover/title/heading-only stubs."""
    return 1.0 if is_low_information_stub(content) else 0.0


def document_masthead_penalty(content: str | None) -> float:
    """Return [0, 1] penalty for short document masthead banners."""
    return 1.0 if is_document_masthead(content) else 0.0
