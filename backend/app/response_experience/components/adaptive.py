"""Adaptive enterprise component enrichment (Phase 5C).

Does not change RX layout selection. Adds presentation components when the
selected layout implies them and extractable content exists.
"""

from __future__ import annotations

from app.response_experience.components import builders as builders
from app.response_experience.components.types import AdaptiveEnrichment, ComponentBuildResult
from app.response_experience.enums import ResponseComponent, ResponseLayoutType
from app.response_experience.types import ResponseLayout

# Layout → adaptive components to attempt (in addition to ResponseLayout.components).
_LAYOUT_ADAPTIVE: dict[ResponseLayoutType, tuple[ResponseComponent, ...]] = {
    ResponseLayoutType.DEFINITION: (
        ResponseComponent.EXECUTIVE_SUMMARY,
        ResponseComponent.KEY_TAKEAWAYS,
    ),
    ResponseLayoutType.WORKFLOW: (
        ResponseComponent.TIMELINE,
        ResponseComponent.CHECKLIST,
    ),
    ResponseLayoutType.TIMELINE: (
        ResponseComponent.TIMELINE,
        ResponseComponent.CHECKLIST,
    ),
    ResponseLayoutType.HIERARCHY: (ResponseComponent.HIERARCHY_TREE,),
    ResponseLayoutType.POLICY: (
        ResponseComponent.CHECKLIST,
        ResponseComponent.IMPORTANT_NOTES,
    ),
    ResponseLayoutType.COMPLIANCE: (
        ResponseComponent.CHECKLIST,
        ResponseComponent.IMPORTANT_NOTES,
    ),
    ResponseLayoutType.GOVERNANCE: (
        ResponseComponent.RESPONSIBILITIES,
        ResponseComponent.RELATED_DOCUMENTS,
    ),
    ResponseLayoutType.COMPARISON: (ResponseComponent.COMPARISON_TABLE,),
    ResponseLayoutType.TABLE_HEAVY: (ResponseComponent.COMPARISON_TABLE,),
    ResponseLayoutType.DECISION_GUIDANCE: (ResponseComponent.DECISION_MATRIX,),
    ResponseLayoutType.EXECUTIVE_REPORT: (
        ResponseComponent.EXECUTIVE_SUMMARY,
        ResponseComponent.KEY_TAKEAWAYS,
        ResponseComponent.RELATED_DOCUMENTS,
    ),
    ResponseLayoutType.EXECUTIVE_SUMMARY: (
        ResponseComponent.EXECUTIVE_SUMMARY,
        ResponseComponent.KEY_TAKEAWAYS,
    ),
    ResponseLayoutType.LIST_EXTRACTION: (ResponseComponent.RELATED_DOCUMENTS,),
    ResponseLayoutType.RELATIONSHIP: (
        ResponseComponent.KEY_TAKEAWAYS,
        ResponseComponent.RELATED_DOCUMENTS,
    ),
}


def requested_components(layout: ResponseLayout) -> list[ResponseComponent]:
    """Union of RX components + adaptive layout components (deterministic)."""
    ordered: list[ResponseComponent] = []
    seen: set[ResponseComponent] = set()
    for component in list(layout.components) + list(
        _LAYOUT_ADAPTIVE.get(layout.layout, ())
    ):
        if component in seen:
            continue
        seen.add(component)
        ordered.append(component)
    return ordered


def _build_one(
    component: ResponseComponent,
    *,
    answer: str,
    existing: str | None,
    related_documents: list[str] | None,
    sources: list[str] | None,
) -> ComponentBuildResult:
    if component == ResponseComponent.EXECUTIVE_SUMMARY:
        return builders.build_executive_summary(answer=answer, existing=existing)
    if component == ResponseComponent.KEY_TAKEAWAYS:
        return builders.build_key_takeaways(answer=answer, existing=existing)
    if component == ResponseComponent.TIMELINE:
        return builders.build_workflow_timeline(answer=answer, existing=existing)
    if component == ResponseComponent.COMPARISON_TABLE:
        return builders.build_comparison_table(answer=answer, existing=existing)
    if component == ResponseComponent.HIERARCHY_TREE:
        return builders.build_hierarchy_tree(answer=answer, existing=existing)
    if component == ResponseComponent.DECISION_MATRIX:
        return builders.build_decision_matrix(answer=answer, existing=existing)
    if component == ResponseComponent.RESPONSIBILITIES:
        return builders.build_responsibility_matrix(answer=answer, existing=existing)
    if component == ResponseComponent.CHECKLIST:
        return builders.build_checklist(answer=answer, existing=existing)
    if component in {
        ResponseComponent.RELATED_DOCUMENTS,
        ResponseComponent.RELATED_STANDARDS,
        ResponseComponent.RELATED_POLICIES,
    }:
        return builders.build_related_documents(
            related_documents=related_documents,
            sources=sources,
            existing=existing,
        )
    if component == ResponseComponent.IMPORTANT_NOTES:
        return builders.build_important_notes(answer=answer, existing=existing)
    # Non-adaptive / passthrough components are left as-is by caller.
    if existing and existing.strip():
        return ComponentBuildResult(
            component=component,
            markdown=existing.strip(),
            skipped=False,
        )
    return ComponentBuildResult(
        component=component,
        markdown=None,
        skipped=True,
        skip_reason="no_content_for_component",
    )


def enrich_with_adaptive_components(
    *,
    layout: ResponseLayout,
    answer: str,
    content_map: dict[ResponseComponent, str],
    related_documents: list[str] | None = None,
    sources: list[str] | None = None,
) -> AdaptiveEnrichment:
    """Enrich content_map with adaptive components; omit empties."""
    requested = requested_components(layout)
    adaptive_targets = set(_LAYOUT_ADAPTIVE.get(layout.layout, ()))
    # Also adaptively enhance components already selected by RX when builders exist.
    enhanceable = set(builders.BUILDERS.keys())

    enriched = dict(content_map)
    results: list[ComponentBuildResult] = []

    for component in requested:
        if component not in adaptive_targets and component not in enhanceable:
            continue
        if component == ResponseComponent.TITLE:
            continue
        if component == ResponseComponent.SOURCES:
            continue

        existing = enriched.get(component)
        result = _build_one(
            component,
            answer=answer,
            existing=existing,
            related_documents=related_documents,
            sources=sources,
        )
        results.append(result)
        if not result.skipped and result.markdown:
            original = (existing or "").strip()
            built = result.markdown.strip()
            # Keep original prose when adaptive chrome reformats a section, so
            # answer content remains present (presentation-only transformation).
            if (
                original
                and original not in built
                and component
                in {
                    ResponseComponent.HIERARCHY_TREE,
                    ResponseComponent.DECISION_MATRIX,
                    ResponseComponent.TIMELINE,
                    ResponseComponent.COMPARISON_TABLE,
                    ResponseComponent.RESPONSIBILITIES,
                    ResponseComponent.CHECKLIST,
                }
            ):
                enriched[component] = f"{built}\n\n{original}"
            else:
                enriched[component] = built

    return AdaptiveEnrichment(
        content_map=enriched,
        components_requested=requested,
        build_results=results,
    )
