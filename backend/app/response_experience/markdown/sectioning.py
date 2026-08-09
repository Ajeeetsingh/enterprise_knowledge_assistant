"""Parse answer text into section blocks without rewriting wording (Phase 5B)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.response_experience.enums import ResponseComponent, ResponseLayoutType
from app.response_experience.markdown.templates import HEADING_ALIASES

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_LEVEL_LINE_RE = re.compile(
    r"^(?:[-*]\s*)?(L[1-4]|Level\s*[1-4])\s*[:.\-–—]\s*(.+)$",
    re.I | re.M,
)


@dataclass
class SectionBlock:
    component: ResponseComponent | None
    heading: str | None
    body: str


@dataclass
class ParsedAnswer:
    """Structural view of the answer; bodies are exact original slices."""

    preamble: str = ""
    blocks: list[SectionBlock] = field(default_factory=list)
    has_headings: bool = False
    has_table: bool = False
    has_numbered_list: bool = False


def parse_answer(answer: str) -> ParsedAnswer:
    text = answer or ""
    parsed = ParsedAnswer(
        has_table="|" in text and re.search(r"^\|.+\|$", text, re.M) is not None,
        has_numbered_list=re.search(r"^\s*\d+\.\s+\S", text, re.M) is not None,
    )
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        parsed.preamble = text.strip()
        return parsed

    parsed.has_headings = True
    first = matches[0]
    if first.start() > 0:
        parsed.preamble = text[: first.start()].strip()

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        heading = match.group(2).strip()
        body = text[start:end].strip()
        component = HEADING_ALIASES.get(heading.lower())
        parsed.blocks.append(
            SectionBlock(component=component, heading=heading, body=body)
        )
    return parsed


def first_paragraph(text: str) -> tuple[str, str]:
    """Split into first paragraph and remainder (exact text, no rewrite)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return "", ""
    parts = _PARAGRAPH_SPLIT_RE.split(cleaned, maxsplit=1)
    if len(parts) == 1:
        # Single paragraph — do not duplicate into summary + body.
        return "", cleaned
    return parts[0].strip(), parts[1].strip()


def format_hierarchy_tree(text: str) -> str | None:
    """If level markers exist, present as tree indentation; keep labels intact."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return None
    hits: list[tuple[int, str]] = []
    for line in lines:
        match = _LEVEL_LINE_RE.match(line)
        if not match:
            # Also accept "L1 Domain" without separator
            soft = re.match(r"^(L[1-4])\s+(.+)$", line, re.I)
            if not soft:
                return None
            level = int(soft.group(1)[1])
            label = soft.group(2).strip()
        else:
            raw = match.group(1)
            digits = re.search(r"[1-4]", raw)
            if not digits:
                return None
            level = int(digits.group(0))
            label = match.group(2).strip()
        hits.append((level, label))
    if len(hits) < 2:
        return None

    out: list[str] = []
    for index, (level, label) in enumerate(hits):
        if level <= 1:
            out.append(f"L{level} {label}" if not label.lower().startswith("l") else label)
            continue
        indent = "    " * (level - 2)
        prefix = "└── "
        out.append(f"{indent}{prefix}L{level} {label}")
    return "\n".join(out)


def main_sink_component(layout: ResponseLayoutType) -> ResponseComponent:
    """Where unsectioned body content is placed for a layout."""
    mapping = {
        ResponseLayoutType.DEFINITION: ResponseComponent.DEFINITION,
        ResponseLayoutType.WORKFLOW: ResponseComponent.STEPS,
        ResponseLayoutType.TIMELINE: ResponseComponent.TIMELINE,
        ResponseLayoutType.COMPARISON: ResponseComponent.COMPARISON_TABLE,
        ResponseLayoutType.HIERARCHY: ResponseComponent.HIERARCHY_TREE,
        ResponseLayoutType.POLICY: ResponseComponent.PURPOSE,
        ResponseLayoutType.GOVERNANCE: ResponseComponent.GOVERNANCE,
        ResponseLayoutType.RELATIONSHIP: ResponseComponent.DETAILED_SECTIONS,
        ResponseLayoutType.DECISION_GUIDANCE: ResponseComponent.DECISION_MATRIX,
        ResponseLayoutType.TROUBLESHOOTING: ResponseComponent.CHECKLIST,
        ResponseLayoutType.REFERENCE_LOOKUP: ResponseComponent.INFORMATION,
        ResponseLayoutType.EXECUTIVE_SUMMARY: ResponseComponent.EXECUTIVE_SUMMARY,
        ResponseLayoutType.EXECUTIVE_REPORT: ResponseComponent.DETAILED_SECTIONS,
        ResponseLayoutType.COMPLIANCE: ResponseComponent.REQUIREMENTS,
        ResponseLayoutType.LONG_REPORT: ResponseComponent.DETAILED_SECTIONS,
        ResponseLayoutType.LIST_EXTRACTION: ResponseComponent.DIRECT_LIST,
        ResponseLayoutType.TABLE_HEAVY: ResponseComponent.COMPARISON_TABLE,
        ResponseLayoutType.MIXED: ResponseComponent.DETAILED_SECTIONS,
    }
    return mapping.get(layout, ResponseComponent.DETAILED_SECTIONS)
