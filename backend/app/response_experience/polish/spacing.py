"""Spacing and heading hierarchy normalization (Phase 5D)."""

from __future__ import annotations

import re

from app.response_experience.polish.style_guide import MAX_PARAGRAPH_CHARS

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
_TRI_NEWLINE_RE = re.compile(r"\n{3,}")


def normalize_heading_hierarchy(markdown: str) -> str:
    """Enforce # title, ## major, ### subsection — never invent headings."""
    lines = (markdown or "").splitlines()
    out: list[str] = []
    seen_title = False
    for line in lines:
        match = _HEADING_RE.match(line)
        if not match:
            out.append(line)
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        if not seen_title:
            out.append(f"# {title}")
            seen_title = True
            continue
        if level >= 3:
            out.append(f"### {title}")
        else:
            out.append(f"## {title}")
    return "\n".join(out)


def split_long_paragraphs(markdown: str) -> str:
    """Break oversized prose paragraphs on sentence boundaries."""
    blocks = re.split(r"\n\s*\n", markdown or "")
    rebuilt: list[str] = []
    for block in blocks:
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith(("#", "|", ">", "-", "*", "•", "✔", "```", "---", "└", "↓")):
            rebuilt.append(stripped)
            continue
        if re.match(r"^\d+\.\s", stripped):
            rebuilt.append(stripped)
            continue
        if len(stripped) <= MAX_PARAGRAPH_CHARS:
            rebuilt.append(stripped)
            continue
        sentences = _SENTENCE_RE.split(stripped)
        if len(sentences) < 2:
            rebuilt.append(stripped)
            continue
        chunk: list[str] = []
        size = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if chunk and size + len(sentence) > MAX_PARAGRAPH_CHARS:
                rebuilt.append(" ".join(chunk))
                chunk = [sentence]
                size = len(sentence)
            else:
                chunk.append(sentence)
                size += len(sentence) + 1
        if chunk:
            rebuilt.append(" ".join(chunk))
    return "\n\n".join(rebuilt)


def normalize_spacing(markdown: str) -> str:
    text = (markdown or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = _TRI_NEWLINE_RE.sub("\n\n", text)
    # Ensure a blank line after headings.
    text = re.sub(r"(#{1,3} [^\n]+)\n(?!\n)", r"\1\n\n", text)
    # Ensure blank line before ##/### except at start.
    text = re.sub(r"([^\n])\n(#{2,3} )", r"\1\n\n\2", text)
    return text.strip()


def collapse_exact_duplicate_sentences(markdown: str) -> str:
    """Remove immediately repeated identical sentences (presentation dedupe)."""
    lines = (markdown or "").splitlines()
    out: list[str] = []
    prev_norm = ""
    for line in lines:
        norm = re.sub(r"\s+", " ", line.strip()).lower()
        if norm and norm == prev_norm and not line.startswith("#"):
            continue
        out.append(line)
        prev_norm = norm
    return "\n".join(out)
