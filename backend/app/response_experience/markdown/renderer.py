"""Enterprise Markdown Renderer (Phase 5B) + Adaptive Components (Phase 5C).

Consumes ResponseLayout + generated answer. Presentation only — does not
rewrite wording or invent facts. Render order comes from ResponseLayout /
COMPONENT_RENDER_PRIORITY (never invented ad hoc).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.response_experience.components.adaptive import enrich_with_adaptive_components
from app.response_experience.enums import ResponseComponent, ResponseLayoutType
from app.response_experience.markdown.sectioning import (
    first_paragraph,
    format_hierarchy_tree,
    main_sink_component,
    parse_answer,
)
from app.response_experience.markdown.templates import heading_for, template_id_for
from app.response_experience.ordering import compute_render_order
from app.response_experience.types import ResponseLayout

_MULTI_SPACE_RE = re.compile(r"[ \t]+\n")
_TRI_NEWLINE_RE = re.compile(r"\n{3,}")


@dataclass
class RenderResult:
    """Rendered markdown plus observability payload."""

    markdown: str
    layout: str
    template_used: str
    render_order: list[str] = field(default_factory=list)
    components_requested: list[str] = field(default_factory=list)
    components_rendered: list[str] = field(default_factory=list)
    components_skipped: list[str] = field(default_factory=list)
    skip_reasons: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "layout_selected": self.layout,
            "markdown_template_used": self.template_used,
            "render_order": list(self.render_order),
            "components_requested": list(self.components_requested),
            "components_rendered": list(self.components_rendered),
            "components_skipped": list(self.components_skipped),
            "skip_reasons": dict(self.skip_reasons),
            "markdown_chars": len(self.markdown),
        }


def _title_text(question: str | None, layout: ResponseLayout) -> str:
    q = (question or "").strip()
    if q:
        return q.rstrip("?").strip() or layout.layout.value.replace("_", " ").title()
    return layout.layout.value.replace("_", " ").title()


def _normalize_whitespace(text: str) -> str:
    """Spacing-only cleanup — does not alter words."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _MULTI_SPACE_RE.sub("\n", text)
    text = _TRI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def _collect_content_map(
    *,
    layout: ResponseLayout,
    answer: str,
) -> dict[ResponseComponent, str]:
    """Map components to exact answer slices (no wording changes)."""
    parsed = parse_answer(answer)
    content: dict[ResponseComponent, str] = {}

    for block in parsed.blocks:
        if block.component is None:
            sink = main_sink_component(layout.layout)
            existing = content.get(sink, "")
            chunk = block.body
            if block.heading:
                chunk = f"**{block.heading}**\n\n{block.body}".strip()
            content[sink] = (existing + "\n\n" + chunk).strip() if existing else chunk
            continue
        existing = content.get(block.component, "")
        content[block.component] = (
            (existing + "\n\n" + block.body).strip() if existing else block.body
        )

    remainder = parsed.preamble.strip()
    if not parsed.has_headings:
        remainder = (answer or "").strip()

    selected = set(layout.components)
    sink = main_sink_component(layout.layout)

    if (
        ResponseComponent.EXECUTIVE_SUMMARY in selected
        and ResponseComponent.EXECUTIVE_SUMMARY not in content
        and remainder
        and len(remainder) >= 500
    ):
        summary, rest = first_paragraph(remainder)
        if summary and rest:
            content[ResponseComponent.EXECUTIVE_SUMMARY] = summary
            remainder = rest

    if remainder:
        if sink in content:
            content[sink] = (content[sink] + "\n\n" + remainder).strip()
        else:
            content[sink] = remainder

    if ResponseComponent.HIERARCHY_TREE in selected and ResponseComponent.HIERARCHY_TREE in content:
        tree = format_hierarchy_tree(content[ResponseComponent.HIERARCHY_TREE])
        if tree:
            content[ResponseComponent.HIERARCHY_TREE] = tree

    return content


def _render_sources(sources: list[str] | None) -> str:
    items = [item.strip() for item in (sources or []) if item and item.strip()]
    if not items:
        return "_No source documents listed._"
    return "\n".join(f"- `{item}`" for item in items)


def _merge_render_order(
    layout: ResponseLayout,
    requested: list[ResponseComponent],
) -> tuple[ResponseComponent, ...]:
    """Respect 5B priorities; include adaptive components via same priority table."""
    base = list(layout.render_order or compute_render_order(layout.components))
    extras = [component for component in requested if component not in base]
    return compute_render_order(base + extras)


def render_enterprise_markdown(
    *,
    layout: ResponseLayout,
    answer: str,
    question: str | None = None,
    sources: list[str] | None = None,
    related_documents: list[str] | None = None,
) -> RenderResult:
    """Render layout-guided markdown with adaptive enterprise components."""
    template = template_id_for(layout.layout)
    content_map = _collect_content_map(layout=layout, answer=answer)

    if related_documents:
        for component in (
            ResponseComponent.RELATED_DOCUMENTS,
            ResponseComponent.RELATED_STANDARDS,
            ResponseComponent.RELATED_POLICIES,
        ):
            if component in layout.components and component not in content_map:
                items = [item.strip() for item in related_documents if item and item.strip()]
                source_set = {(s or "").strip().lower() for s in (sources or [])}
                related = [item for item in items if item.lower() not in source_set]
                if related:
                    content_map[component] = "\n".join(f"- {item}" for item in related)

    enrichment = enrich_with_adaptive_components(
        layout=layout,
        answer=answer,
        content_map=content_map,
        related_documents=related_documents,
        sources=sources,
    )
    content_map = enrichment.content_map
    requested = enrichment.components_requested
    order = _merge_render_order(layout, requested)

    if ResponseComponent.SOURCES in requested or ResponseComponent.SOURCES in layout.components:
        content_map[ResponseComponent.SOURCES] = _render_sources(sources)

    parts: list[str] = []
    rendered: list[str] = []
    skipped: list[str] = []
    skip_reasons = dict(enrichment.skip_reasons)

    for component in order:
        if component == ResponseComponent.TITLE:
            parts.append(f"# {_title_text(question, layout)}")
            rendered.append(component.value)
            continue

        body = (content_map.get(component) or "").strip()
        if not body:
            skipped.append(component.value)
            skip_reasons.setdefault(component.value, "empty_after_adaptive_build")
            continue

        heading = heading_for(layout.layout, component)
        parts.append(f"## {heading}")
        parts.append("")
        parts.append(body)
        rendered.append(component.value)

    markdown = _normalize_whitespace("\n\n".join(parts))
    if len(rendered) >= 3:
        markdown = _insert_horizontal_rules(markdown)

    return RenderResult(
        markdown=markdown,
        layout=layout.layout.value,
        template_used=template,
        render_order=[item.value for item in order],
        components_requested=[item.value for item in requested],
        components_rendered=rendered,
        components_skipped=skipped,
        skip_reasons=skip_reasons,
    )


def _insert_horizontal_rules(markdown: str) -> str:
    """Insert --- before H2 sections except the first H2 after title."""
    lines = markdown.split("\n")
    out: list[str] = []
    h2_count = 0
    for line in lines:
        if line.startswith("## "):
            h2_count += 1
            if h2_count >= 2:
                while out and out[-1] == "":
                    out.pop()
                out.append("")
                out.append("---")
                out.append("")
        out.append(line)
    return "\n".join(out)


def content_preserved(original: str, rendered: str) -> bool:
    """True when every non-trivial original token sequence remains present.

    Allows added headings, rules, component chrome, source lists, list
    reformatting, and restrained emphasis markers.
    """
    rendered_plain = re.sub(r"[*_`>#|•✔↓└─]+", " ", rendered or "")
    rendered_norm = re.sub(r"\s+", " ", rendered_plain)
    rendered_lower = rendered_norm.lower()
    orig_paras = [
        re.sub(r"\s+", " ", para).strip()
        for para in _PARAGRAPH_SPLIT_SAFE(original)
        if len(para.strip()) >= 12
    ]
    if not orig_paras:
        body = re.sub(r"\s+", " ", (original or "").strip())
        return (not body) or (body in rendered_norm)

    for para in orig_paras:
        if para in rendered_norm:
            continue
        # Presentation may split enumerations into bullets — require content words.
        words = [word for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]{2,}", para)]
        if words and all(word.lower() in rendered_lower for word in words):
            continue
        return False
    return True


def _PARAGRAPH_SPLIT_SAFE(text: str) -> list[str]:
    return re.split(r"\n\s*\n+", text or "")
