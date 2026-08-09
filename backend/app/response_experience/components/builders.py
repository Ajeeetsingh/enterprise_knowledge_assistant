"""Build adaptive enterprise markdown components from existing answer text."""

from __future__ import annotations

import re

from app.response_experience.components.extractors import (
    extract_comparison_entities,
    extract_decision_fields,
    extract_level_rows,
    extract_list_items,
    extract_note_sentences,
    extract_role_rows,
    extract_step_labels,
    pretty_document_name,
    split_sentences,
)
from app.response_experience.components.types import ComponentBuildResult
from app.response_experience.enums import ResponseComponent
from app.response_experience.markdown.sectioning import first_paragraph, format_hierarchy_tree


def _ok(component: ResponseComponent, markdown: str) -> ComponentBuildResult:
    return ComponentBuildResult(
        component=component,
        markdown=markdown.strip(),
        skipped=False,
    )


def _skip(component: ResponseComponent, reason: str) -> ComponentBuildResult:
    return ComponentBuildResult(
        component=component,
        markdown=None,
        skipped=True,
        skip_reason=reason,
    )


def build_executive_summary(
    *,
    answer: str,
    existing: str | None,
) -> ComponentBuildResult:
    component = ResponseComponent.EXECUTIVE_SUMMARY
    if existing and existing.strip():
        # Present as a summary callout without changing wording.
        body = existing.strip()
        return _ok(component, f"> {body}")

    text = (answer or "").strip()
    if len(text) < 180:
        return _skip(component, "answer_too_short_for_summary")

    summary, rest = first_paragraph(text)
    if summary and rest:
        return _ok(component, f"> {summary}")

    # Medium single-block answers: use first sentence only as summary chrome.
    sentences = split_sentences(text)
    if len(sentences) >= 2 and len(text) >= 160:
        return _ok(component, f"> {sentences[0]}")
    return _skip(component, "insufficient_summary_span")


def build_key_takeaways(
    *,
    answer: str,
    existing: str | None,
) -> ComponentBuildResult:
    component = ResponseComponent.KEY_TAKEAWAYS
    if existing and existing.strip() and re.search(r"^[-*•]", existing, re.M):
        return _ok(component, existing.strip())

    items = extract_list_items(answer)
    if len(items) < 2:
        sentences = split_sentences(answer)
        # Prefer concise factual sentences; keep original wording.
        items = [sentence.rstrip(".") for sentence in sentences[:5] if len(sentence) <= 160]
    if len(items) < 2:
        return _skip(component, "fewer_than_two_extractable_points")
    bullets = "\n".join(f"• {item}" for item in items[:6])
    return _ok(component, bullets)


def build_workflow_timeline(
    *,
    answer: str,
    existing: str | None,
) -> ComponentBuildResult:
    component = ResponseComponent.TIMELINE
    source = existing or answer
    labels = extract_step_labels(source)
    if len(labels) < 3:
        return _skip(component, "fewer_than_three_workflow_steps")
    lines: list[str] = []
    for index, label in enumerate(labels):
        lines.append(label)
        if index < len(labels) - 1:
            lines.append("↓")
    return _ok(component, "\n\n".join(lines))


def build_comparison_table(
    *,
    answer: str,
    existing: str | None,
) -> ComponentBuildResult:
    component = ResponseComponent.COMPARISON_TABLE
    if existing and "|" in existing and re.search(r"^\|.+\|$", existing, re.M):
        return _ok(component, existing.strip())

    entities = extract_comparison_entities(answer)
    if not entities:
        return _skip(component, "no_comparable_entities_detected")
    left, right = entities
    # Only structural headers + entity names already in the answer — no fabricated features.
    table = (
        f"| Aspect | {left} | {right} |\n"
        f"| --- | --- | --- |\n"
        f"| Entity | {left} | {right} |"
    )
    return _ok(component, table)


def build_hierarchy_tree(
    *,
    answer: str,
    existing: str | None,
) -> ComponentBuildResult:
    component = ResponseComponent.HIERARCHY_TREE
    source = existing or answer
    tree = format_hierarchy_tree(source)
    if tree:
        return _ok(component, tree)
    rows = extract_level_rows(source)
    if len(rows) < 2:
        return _skip(component, "no_nested_hierarchy_markers")
    lines: list[str] = []
    for level, label in rows:
        if level <= 1:
            lines.append(f"L{level} {label}")
        else:
            indent = "    " * (level - 2)
            lines.append(f"{indent}└── L{level} {label}")
    return _ok(component, "\n".join(lines))


def build_decision_matrix(
    *,
    answer: str,
    existing: str | None,
) -> ComponentBuildResult:
    component = ResponseComponent.DECISION_MATRIX
    if existing and "|" in existing:
        return _ok(component, existing.strip())

    fields = extract_decision_fields(answer)
    if "committee" not in fields and "escalation" not in fields:
        return _skip(component, "no_decision_path_signals")

    rows: list[tuple[str, str]] = []
    for stage in ("situation", "committee", "escalation"):
        value = fields.get(stage)
        if value:
            rows.append((stage.title(), value))
    if len(rows) < 2:
        return _skip(component, "insufficient_decision_fields")

    flow_stages = [stage for stage, _ in rows]
    flow = "\n\n↓\n\n".join(flow_stages)
    table_lines = ["| Stage | Detail |", "| --- | --- |"]
    for stage, value in rows:
        table_lines.append(f"| {stage} | {value.replace('|', '/')} |")
    return _ok(component, f"{flow}\n\n" + "\n".join(table_lines))


def build_responsibility_matrix(
    *,
    answer: str,
    existing: str | None,
) -> ComponentBuildResult:
    component = ResponseComponent.RESPONSIBILITIES
    if existing and "|" in existing:
        return _ok(component, existing.strip())

    rows = extract_role_rows(existing or answer)
    if len(rows) < 2:
        return _skip(component, "fewer_than_two_role_responsibility_rows")
    lines = ["| Role | Responsibility |", "| --- | --- |"]
    for role, responsibility in rows:
        safe_role = role.replace("|", "/")
        safe_resp = responsibility.replace("|", "/")
        lines.append(f"| {safe_role} | {safe_resp} |")
    return _ok(component, "\n".join(lines))


def build_checklist(
    *,
    answer: str,
    existing: str | None,
) -> ComponentBuildResult:
    component = ResponseComponent.CHECKLIST
    items = extract_list_items(existing or answer)
    if len(items) < 2:
        # Fall back to short actionable sentences.
        items = [
            sentence.rstrip(".")
            for sentence in split_sentences(answer)
            if re.search(r"\b(must|shall|require|complete|assign|verify|publish|approv)", sentence, re.I)
        ]
    if len(items) < 2:
        labels = extract_step_labels(answer)
        items = labels
    if len(items) < 2:
        return _skip(component, "fewer_than_two_checklist_items")
    return _ok(component, "\n".join(f"✔ {item}" for item in items[:8]))


def build_related_documents(
    *,
    related_documents: list[str] | None,
    sources: list[str] | None,
    existing: str | None,
) -> ComponentBuildResult:
    component = ResponseComponent.RELATED_DOCUMENTS
    if existing and existing.strip():
        return _ok(component, existing.strip())

    source_set = {(item or "").strip().lower() for item in (sources or []) if item}
    related: list[str] = []
    for item in related_documents or []:
        cleaned = (item or "").strip()
        if not cleaned:
            continue
        if cleaned.lower() in source_set:
            continue
        related.append(pretty_document_name(cleaned))
    # Deduplicate
    deduped: list[str] = []
    seen: set[str] = set()
    for name in related:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(name)
    if not deduped:
        return _skip(component, "no_semantic_related_documents")
    return _ok(component, "\n".join(f"• {name}" for name in deduped))


def build_important_notes(
    *,
    answer: str,
    existing: str | None,
) -> ComponentBuildResult:
    component = ResponseComponent.IMPORTANT_NOTES
    if existing and existing.strip():
        notes = extract_note_sentences(existing) or [existing.strip()]
    else:
        notes = extract_note_sentences(answer)
    if not notes:
        return _skip(component, "no_meaningful_note_sentences")
    body = "\n\n".join(f"> **Note:** {note}" for note in notes[:4])
    return _ok(component, body)


BUILDERS = {
    ResponseComponent.EXECUTIVE_SUMMARY: "executive_summary",
    ResponseComponent.KEY_TAKEAWAYS: "key_takeaways",
    ResponseComponent.TIMELINE: "timeline",
    ResponseComponent.COMPARISON_TABLE: "comparison_table",
    ResponseComponent.HIERARCHY_TREE: "hierarchy_tree",
    ResponseComponent.DECISION_MATRIX: "decision_matrix",
    ResponseComponent.RESPONSIBILITIES: "responsibility_matrix",
    ResponseComponent.CHECKLIST: "checklist",
    ResponseComponent.RELATED_DOCUMENTS: "related_documents",
    ResponseComponent.RELATED_STANDARDS: "related_documents",
    ResponseComponent.RELATED_POLICIES: "related_documents",
    ResponseComponent.IMPORTANT_NOTES: "important_notes",
}
