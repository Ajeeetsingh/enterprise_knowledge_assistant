"""Query normalization — case, spacing, punctuation, aliases."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.knowledge_registry.aliases.catalog import build_alias_lookup


@dataclass
class NormalizationResult:
    original: str
    normalized: str
    aliases_applied: list[dict[str, str]]
    quoted_phrases: list[str]


_PUNCT_RE = re.compile(r"[^\w\s\"'/.-]+", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")
_QUOTE_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')


class QueryNormalizer:
    """Normalize user queries and expand registry aliases when available."""

    def __init__(self, alias_lookup: dict[str, str] | None = None) -> None:
        self._aliases = alias_lookup if alias_lookup is not None else build_alias_lookup()

    def normalize(self, query: str) -> NormalizationResult:
        original = query or ""
        quoted = []
        for match in _QUOTE_RE.finditer(original):
            phrase = match.group(1) or match.group(2)
            if phrase:
                quoted.append(phrase.strip())

        text = original.strip().lower()
        text = _PUNCT_RE.sub(" ", text)
        text = text.replace('"', " ").replace("'", " ")
        text = _SPACE_RE.sub(" ", text).strip()

        aliases_applied: list[dict[str, str]] = []
        # Apply longer aliases first to avoid partial overwrites.
        for alias in sorted(self._aliases.keys(), key=len, reverse=True):
            if not alias:
                continue
            pattern = re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)", re.IGNORECASE)
            if pattern.search(text):
                canonical = self._aliases[alias]
                text = pattern.sub(canonical, text)
                aliases_applied.append({"alias": alias, "canonical": canonical})

        # Title-case multi-word canonical replacements already inserted; keep spacing clean.
        text = _SPACE_RE.sub(" ", text).strip()
        # Prefer readable casing: capitalize words that look like canonical titles.
        normalized = self._prettify(text)
        return NormalizationResult(
            original=original,
            normalized=normalized,
            aliases_applied=aliases_applied,
            quoted_phrases=quoted,
        )

    @staticmethod
    def _prettify(text: str) -> str:
        parts = []
        for token in text.split(" "):
            if not token:
                continue
            if token.isupper() and len(token) <= 4:
                parts.append(token)
            elif "/" in token:
                parts.append("/".join(p.capitalize() for p in token.split("/")))
            else:
                parts.append(token[:1].upper() + token[1:] if token else token)
        return " ".join(parts)
