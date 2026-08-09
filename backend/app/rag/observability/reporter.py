"""Human-readable RAG diagnostic reports."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from app.rag.observability.models import ChunkHitTrace, RagDiagnosticReport


def _section(title: str) -> str:
    return f"\n{'-' * 52}\n{title}\n{'-' * 52}\n"


def _fmt_hit(hit: ChunkHitTrace) -> str:
    lines = [
        f"Rank {hit.rank}",
        f"Document: {hit.document}",
        f"Filename: {hit.filename}",
        f"Page: {hit.page}",
        f"Chunk ID: {hit.chunk_id}",
        f"Chunk type: {hit.chunk_type}",
        f"Dense score: {hit.dense_score}",
        f"BM25 score: {hit.bm25_score}",
        f"Fusion (RRF) score: {hit.fusion_score}",
        f"Metadata bonus: {hit.metadata_bonus}",
        f"Metadata/final score: {hit.metadata_final_score}",
        f"CrossEncoder score: {hit.cross_encoder_score}",
        f"Final score: {hit.final_score}",
        f"Selected for context: {hit.selected_for_context}",
    ]
    if hit.found_by_queries:
        lines.append("Found by queries:")
        for q in hit.found_by_queries:
            lines.append(f"  - {q}")
    lines.append("Preview:")
    lines.append(hit.preview or "")
    lines.append("")
    return "\n".join(lines)


def render_diagnostic_report(report: RagDiagnosticReport) -> str:
    parts: list[str] = []
    parts.append("=" * 52)
    parts.append("RAG DIAGNOSTIC REPORT")
    parts.append("=" * 52)

    parts.append(_section("QUESTION"))
    parts.append(report.question)

    parts.append(_section("QUERY UNDERSTANDING / EXPANSION"))
    understanding = report.understanding or {}
    parts.append(f"Intent: {understanding.get('intent')}")
    parts.append(f"Entities: {understanding.get('entities')}")
    parts.append(f"Concepts: {understanding.get('concepts')}")
    parts.append(f"Likely documents: {understanding.get('likely_documents')}")
    parts.append(f"Expansion strategy: {report.expansion_strategy}")
    parts.append("Generated retrieval queries:")
    for index, query in enumerate(report.expansion_queries, start=1):
        parts.append(f"  {index}. {query}")

    for per in report.per_query:
        parts.append(_section(f"EXPANDED QUERY RETRIEVAL — {per.retrieval_query!r}"))
        parts.append("BM25 RESULTS")
        parts.append("\n".join(_fmt_hit(h) for h in per.bm25_hits) or "(none)\n")
        parts.append("VECTOR / DENSE RESULTS")
        parts.append("\n".join(_fmt_hit(h) for h in per.dense_hits) or "(none)\n")
        parts.append("FUSION (RRF) RESULTS")
        parts.append("\n".join(_fmt_hit(h) for h in per.fusion_hits) or "(none)\n")
        parts.append("METADATA-RESCORDED TOP-K")
        parts.append("\n".join(_fmt_hit(h) for h in per.metadata_hits) or "(none)\n")

    parts.append(_section("MULTI-QUERY MERGE (POST FUSION ACROSS EXPANSIONS)"))
    parts.append("\n".join(_fmt_hit(h) for h in report.post_fusion_merge) or "(none)\n")

    parts.append(_section("RERANK"))
    parts.append("\n".join(_fmt_hit(h) for h in report.post_rerank) or "(none)\n")

    parts.append(_section("FINAL CONTEXT (SENT TO LLM)"))
    parts.append(f"Character count: {report.final_context_chars}")
    parts.append(f"Approx tokens: {report.final_context_approx_tokens}")
    parts.append(f"Context order count: {len(report.final_context)}")
    for chunk in report.final_context:
        parts.append(f"\nChunk {chunk.order}")
        parts.append(f"Document: {chunk.document}")
        parts.append(f"Page: {chunk.page}")
        parts.append(f"Chunk ID: {chunk.chunk_id}")
        parts.append(f"Chunk type: {chunk.chunk_type}")
        if chunk.found_by_queries:
            parts.append("Found by queries:")
            for q in chunk.found_by_queries:
                parts.append(f"  - {q}")
        parts.append("Preview:")
        parts.append(chunk.preview)
        parts.append("-" * 20)

    parts.append(_section("MISSING / EXPECTED CHUNK DETECTION"))
    if not report.expected_chunk_verdicts:
        parts.append("(no expected signatures configured for this question)")
    for verdict in report.expected_chunk_verdicts:
        parts.append(f"Label: {verdict.label}")
        parts.append(f"Signature: {verdict.signature}")
        parts.append(f"Expected chunk: {verdict.expected_chunk_id}")
        parts.append(f"Document: {verdict.expected_document} page={verdict.expected_page}")
        parts.append(f"Retrieved: {'YES' if verdict.retrieved else 'NO'}")
        parts.append(f"Best rank: {verdict.best_rank}")
        parts.append(f"Fate: {verdict.fate}")
        parts.append(f"Stages seen: {verdict.stages_seen}")
        if verdict.expected_preview:
            parts.append("Expected preview:")
            parts.append(verdict.expected_preview)
        parts.append("")

    parts.append(_section("ANSWER PLANNING (PHASE 4A)"))
    plan = report.answer_plan or {}
    if not plan:
        parts.append("(not captured)")
    else:
        parts.append(f"Question Type: {plan.get('question_type')}")
        parts.append(f"Planner Decision: {plan.get('planner_decision')}")
        parts.append(f"Blueprint Selected: {plan.get('blueprint_selected')}")
        parts.append(f"Reason: {plan.get('reason')}")
        sections = plan.get("sections") or []
        if sections:
            parts.append("Recommended Structure:")
            for index, section in enumerate(sections, start=1):
                parts.append(f"  {index}. {section}")
        signals = plan.get("matched_signals") or []
        if signals:
            parts.append(f"Matched signals: {signals}")

    parts.append(_section("EVIDENCE ORGANIZATION (PHASE 4B)"))
    graph = report.evidence_graph or {}
    if not graph:
        parts.append("(not captured)")
    else:
        parts.append(f"Structure profile: {graph.get('structure_profile')}")
        parts.append(f"Answer type: {graph.get('answer_type')}")
        parts.append(f"Node count: {graph.get('node_count')}")
        parts.append("Ordering decisions:")
        for decision in graph.get("ordering_decisions") or []:
            parts.append(f"  - {decision}")
        parts.append("Evidence groups / hierarchy:")
        for node in graph.get("nodes") or []:
            parts.append(
                f"  - {node.get('label')} [{node.get('structure_kind')}] "
                f"chunks={node.get('chunk_ids')} children={node.get('child_ids')}"
            )
        links = graph.get("links") or []
        if links:
            parts.append("Relationship links:")
            for link in links:
                parts.append(
                    f"  - {link.get('from')} -> {link.get('to')} "
                    f"({link.get('relation')}; {link.get('reason')})"
                )

    parts.append(_section("ANSWER COMPOSITION (PHASE 4C)"))
    composition = report.answer_composition or {}
    if not composition:
        parts.append("(not captured)")
    else:
        parts.append(f"Answer type: {composition.get('answer_type')}")
        parts.append(f"Structure profile: {composition.get('structure_profile')}")
        parts.append("Priority scores:")
        for row in composition.get("priority_scores") or []:
            parts.append(
                f"  - {row.get('label')}: {row.get('priority')} "
                f"score={row.get('score')} reasons={row.get('reasons')}"
            )
        final = composition.get("final_composition") or {}
        parts.append(f"Primary Evidence: {final.get('primary')}")
        parts.append(f"Supporting Evidence: {final.get('supporting')}")
        parts.append(f"Optional Evidence: {final.get('optional')}")
        parts.append("Decisions:")
        for decision in composition.get("decisions") or []:
            parts.append(f"  - {decision}")

    parts.append(_section("ANSWER SYNTHESIS (PHASE 4F)"))
    synthesis = report.answer_synthesis or {}
    if not synthesis:
        parts.append("(not captured)")
    else:
        parts.append(f"Mode: {synthesis.get('mode')}")
        parts.append(f"Primary document: {synthesis.get('primary_document')}")
        parts.append(f"Supporting documents: {synthesis.get('supporting_documents')}")
        parts.append(f"Context documents: {synthesis.get('context_documents')}")
        parts.append(f"Concept flow: {synthesis.get('concept_flow')}")
        parts.append(f"Concept coverage: {synthesis.get('concept_coverage')}")
        parts.append(f"Dropped concepts: {synthesis.get('dropped_concepts')}")
        parts.append(f"Unsupported concepts: {synthesis.get('unsupported_concepts')}")
        contrib = synthesis.get("document_contribution_pct") or {}
        if contrib:
            parts.append("Document contribution %:")
            for source, pct in contrib.items():
                parts.append(f"  - {source}: {pct}")
        parts.append("Section ownership:")
        for row in synthesis.get("section_ownership") or []:
            parts.append(
                f"  - {row.get('concept')}: role={row.get('owner_role')} "
                f"sources={row.get('sources')}"
            )
        parts.append(f"Unsupported request: {synthesis.get('is_unsupported')}")
        if synthesis.get("refusal_message"):
            parts.append(f"Refusal message: {synthesis.get('refusal_message')}")
        parts.append("Decisions:")
        for decision in synthesis.get("decisions") or []:
            parts.append(f"  - {decision}")

    parts.append(_section("GAQA (PHASE 4D/4E)"))
    gaqa = report.gaqa_report or {}
    if not gaqa:
        parts.append("(not captured)")
    else:
        quality = gaqa.get("quality_score") or {}
        confidence = gaqa.get("confidence_breakdown") or {}
        parts.append(f"Coverage: {quality.get('coverage')}")
        parts.append(f"Grounding: {quality.get('grounding')}")
        parts.append(f"Blueprint: {quality.get('blueprint')}")
        parts.append(f"Redundancy penalty: {quality.get('redundancy')}")
        parts.append(f"Unsupported claims rate: {quality.get('unsupported_claims')}")
        parts.append(f"Overall quality: {quality.get('overall')}")
        parts.append(f"Intent coverage: {gaqa.get('intent_coverage')}")
        parts.append(f"Evidence specificity: {gaqa.get('evidence_specificity')}")
        parts.append(f"Question match: {gaqa.get('question_match')}")
        parts.append(f"Answer completeness: {gaqa.get('answer_completeness')}")
        parts.append(f"Refusal reason: {gaqa.get('refusal_reason') or '(none)'}")
        parts.append(
            f"Overall reliability score: {gaqa.get('overall_reliability_score')}"
        )
        parts.append(
            f"Confidence: {confidence.get('label')} "
            f"({confidence.get('overall_confidence')})"
        )
        components = confidence.get("components") or {}
        if components:
            parts.append("Confidence breakdown:")
            for key, value in components.items():
                parts.append(f"  - {key}: {value}")
        missing = gaqa.get("missing_concepts") or []
        parts.append(f"Missing concepts: {missing if missing else '(none)'}")
        notes = gaqa.get("reliability_notes") or []
        parts.append(f"Reliability notes: {notes if notes else '(none)'}")
        blueprint = gaqa.get("blueprint_validation") or {}
        parts.append(f"Blueprint compliance: {blueprint.get('compliance')}")
        for section in blueprint.get("sections") or []:
            mark = "YES" if section.get("present") else "NO"
            parts.append(f"  - [{mark}] {section.get('section')}")
        parts.append("Evidence mapping:")
        for mapping in gaqa.get("evidence_mapping") or []:
            parts.append(
                f"  - {mapping.get('label')} -> {mapping.get('source')} "
                f"chunks={mapping.get('chunk_ids')} support={mapping.get('support')}"
            )
        ordering = gaqa.get("ordering") or {}
        parts.append(f"Ordering ok: {ordering.get('ok')}")
        for note in ordering.get("notes") or []:
            parts.append(f"  - {note}")
        if gaqa.get("recommended_final_answer"):
            parts.append("Recommended final answer override: YES")

    parts.append(_section("RESPONSE EXPERIENCE (PHASE 5A)"))
    rx = report.response_layout or {}
    if not rx:
        parts.append("(not captured)")
    else:
        parts.append(f"Response Layout: {rx.get('response_layout') or rx.get('layout')}")
        parts.append(f"Layout Decision: {rx.get('layout_decision')}")
        parts.append(f"Expected Render Type: {rx.get('expected_render_type')}")
        parts.append(f"Render Order: {rx.get('render_order')}")
        parts.append(f"Component Priorities: {rx.get('component_priorities')}")
        parts.append(f"Reason: {rx.get('reason')}")
        parts.append(
            f"Components Selected: {rx.get('components_selected') or rx.get('components')}"
        )
        parts.append(f"Page structure: {rx.get('page_structure')}")
        parts.append(f"Visual emphasis: {rx.get('visual_emphasis')}")
        parts.append(f"Adaptive flags: {rx.get('adaptive_flags')}")
        parts.append("Decisions:")
        for decision in rx.get("decisions") or []:
            parts.append(f"  - {decision}")

    parts.append(_section("MARKDOWN RENDER (PHASE 5B)"))
    md = report.markdown_render or (rx.get("render") if rx else {}) or {}
    if not md:
        parts.append("(not captured)")
    else:
        parts.append(f"Layout Selected: {md.get('layout_selected')}")
        parts.append(f"Markdown Template Used: {md.get('markdown_template_used')}")
        parts.append(f"Render Order: {md.get('render_order')}")
        parts.append(f"Components Requested: {md.get('components_requested')}")
        parts.append(f"Components Rendered: {md.get('components_rendered')}")
        parts.append(f"Components Skipped: {md.get('components_skipped')}")
        reasons = md.get("skip_reasons") or {}
        if reasons:
            parts.append("Reason for Skipping:")
            for key, value in reasons.items():
                parts.append(f"  - {key}: {value}")
        parts.append(f"Markdown chars: {md.get('markdown_chars')}")

    parts.append(_section("PRESENTATION POLISH (PHASE 5D)"))
    polish = report.presentation_polish or {}
    if not polish:
        parts.append("(not captured)")
    else:
        parts.append(f"Transforms applied: {polish.get('transforms_applied')}")
        parts.append(f"Markdown chars: {polish.get('markdown_chars')}")

    parts.append(_section("PRESENTATION FINALIZE (PHASE 5E)"))
    finalize = report.presentation_finalize or {}
    if not finalize:
        parts.append("(not captured)")
    else:
        parts.append(f"Transforms applied: {finalize.get('transforms_applied')}")
        parts.append(f"Empty sections removed: {finalize.get('empty_sections_removed')}")
        parts.append(f"Validation OK: {finalize.get('validation_ok')}")
        issues = finalize.get("validation_issues") or []
        if issues:
            parts.append("Validation issues:")
            for issue in issues:
                parts.append(f"  - {issue}")
        parts.append(f"Content preserved: {finalize.get('content_preserved')}")
        parts.append(f"Markdown chars: {finalize.get('markdown_chars')}")

    parts.append(_section("RAW MODEL OUTPUT"))
    parts.append(report.model_output or "(not captured)")

    parts.append(_section("FINAL RESPONSE"))
    parts.append(f"Answer kind: {report.answer_kind}")
    parts.append(report.final_answer or "(not captured)")

    if report.errors:
        parts.append(_section("ERRORS"))
        for err in report.errors:
            parts.append(f"- {err}")

    parts.append("\n" + "=" * 52)
    return "\n".join(parts)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return (slug[:60] or "query")


def write_diagnostic_report(
    report: RagDiagnosticReport,
    rendered: str,
    *,
    output_dir: Path | None = None,
) -> Path | None:
    """Write markdown/text + JSON report under storage/diagnostics."""
    try:
        from app.config import get_settings

        base = output_dir or (get_settings().storage_path / "diagnostics")
    except Exception:  # noqa: BLE001
        base = output_dir or Path("storage/diagnostics")

    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{stamp}_{_slug(report.question)}"
    text_path = base / f"{stem}.txt"
    json_path = base / f"{stem}.json"
    text_path.write_text(rendered, encoding="utf-8")
    json_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return text_path
