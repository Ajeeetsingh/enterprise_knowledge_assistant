"""Executive Summary refinement — concise, non-repetitive (Phase 5D)."""

from __future__ import annotations

import re

from app.response_experience.polish.style_guide import MAX_SUMMARY_SENTENCES

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    cleaned = cleaned.lstrip("> ").strip()
    if not cleaned:
        return []
    parts = _SENTENCE_RE.split(cleaned)
    return [part.strip() for part in parts if part.strip()]


def refine_executive_summary(markdown: str) -> str:
    """Tighten Executive Summary using only existing sentences."""
    lines = (markdown or "").splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not re.match(r"^##\s+Executive Summary\s*$", line, re.I):
            out.append(line)
            index += 1
            continue

        out.append(line)
        index += 1
        # Skip blank lines after heading.
        while index < len(lines) and not lines[index].strip():
            index += 1

        body_lines: list[str] = []
        while index < len(lines) and not lines[index].startswith("## "):
            body_lines.append(lines[index])
            index += 1

        body = "\n".join(body_lines).strip()
        # Collect following section text to drop duplicated lead sentences.
        following = ""
        look = index
        if look < len(lines) and lines[look].startswith("## "):
            look += 1
            follow_parts: list[str] = []
            while look < len(lines) and not lines[look].startswith("## "):
                follow_parts.append(lines[look])
                look += 1
            following = "\n".join(follow_parts)

        sentences = _sentences(re.sub(r"^>\s?", "", body, flags=re.M))
        follow_norm = re.sub(r"\s+", " ", following).lower()
        kept: list[str] = []
        for sentence in sentences:
            norm = re.sub(r"\s+", " ", sentence).lower().strip()
            if norm and norm in follow_norm:
                continue
            kept.append(sentence)
            if len(kept) >= MAX_SUMMARY_SENTENCES:
                break
        if not kept and sentences:
            kept = sentences[:1]

        if kept:
            out.append("")
            out.append("> " + " ".join(kept))
            out.append("")
        elif body:
            out.append("")
            out.append(body)
            out.append("")
    return "\n".join(out)
