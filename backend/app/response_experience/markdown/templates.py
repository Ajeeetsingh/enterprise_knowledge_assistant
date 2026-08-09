"""Heading titles and template ids per layout/component (Phase 5B)."""

from __future__ import annotations

from app.response_experience.enums import ResponseComponent, ResponseLayoutType

# Default H2 title for each component.
COMPONENT_HEADINGS: dict[ResponseComponent, str] = {
    ResponseComponent.TITLE: "Title",
    ResponseComponent.EXECUTIVE_SUMMARY: "Executive Summary",
    ResponseComponent.KEY_TAKEAWAYS: "Key Takeaways",
    ResponseComponent.DEFINITION: "Definition",
    ResponseComponent.PURPOSE: "Purpose",
    ResponseComponent.KEY_CHARACTERISTICS: "Key Characteristics",
    ResponseComponent.IMPORTANT_NOTES: "Important Notes",
    ResponseComponent.WARNING: "Warning",
    ResponseComponent.INFORMATION: "Information",
    ResponseComponent.CHECKLIST: "Checklist",
    ResponseComponent.TIMELINE: "Timeline",
    ResponseComponent.STEPS: "Workflow Steps",
    ResponseComponent.HIERARCHY_TREE: "Hierarchy",
    ResponseComponent.DECISION_MATRIX: "Decision Summary",
    ResponseComponent.COMPARISON_TABLE: "Comparison",
    ResponseComponent.RELATIONSHIP_DIAGRAM: "Relationship",
    ResponseComponent.RESPONSIBILITIES: "Responsibilities",
    ResponseComponent.REQUIREMENTS: "Requirements",
    ResponseComponent.EXCEPTIONS: "Exceptions",
    ResponseComponent.SCOPE: "Scope",
    ResponseComponent.GOVERNANCE: "Governance",
    ResponseComponent.OBJECTIVE: "Objective",
    ResponseComponent.OUTCOME: "Outcome",
    ResponseComponent.RELATED_DOCUMENTS: "Related Documents",
    ResponseComponent.RELATED_STANDARDS: "Related Standards",
    ResponseComponent.RELATED_POLICIES: "Related Policies",
    ResponseComponent.FREQUENTLY_REFERENCED_POLICIES: "Frequently Referenced Policies",
    ResponseComponent.RECOMMENDATIONS: "Recommendations",
    ResponseComponent.KEY_DIFFERENCES: "Key Differences",
    ResponseComponent.OWNER: "Owner",
    ResponseComponent.REVIEW_CYCLE: "Review Cycle",
    ResponseComponent.SOURCES: "Sources",
    ResponseComponent.DETAILED_SECTIONS: "Detailed Analysis",
    ResponseComponent.DIRECT_LIST: "Direct Answer",
}

# Layout-specific heading overrides.
_LAYOUT_HEADING_OVERRIDES: dict[
    ResponseLayoutType, dict[ResponseComponent, str]
] = {
    ResponseLayoutType.RELATIONSHIP: {
        ResponseComponent.EXECUTIVE_SUMMARY: "Overview",
        ResponseComponent.DETAILED_SECTIONS: "Concepts",
        ResponseComponent.RELATIONSHIP_DIAGRAM: "Relationship",
        ResponseComponent.KEY_TAKEAWAYS: "Business Impact",
    },
    ResponseLayoutType.DECISION_GUIDANCE: {
        ResponseComponent.DECISION_MATRIX: "Decision Summary",
        ResponseComponent.RECOMMENDATIONS: "Recommended Path",
        ResponseComponent.IMPORTANT_NOTES: "Constraints",
        ResponseComponent.DETAILED_SECTIONS: "Criteria",
        ResponseComponent.KEY_TAKEAWAYS: "Next Steps",
    },
    ResponseLayoutType.EXECUTIVE_REPORT: {
        ResponseComponent.DETAILED_SECTIONS: "Detailed Analysis",
        ResponseComponent.KEY_TAKEAWAYS: "Key Findings",
    },
    ResponseLayoutType.WORKFLOW: {
        ResponseComponent.STEPS: "Workflow Steps",
        ResponseComponent.RESPONSIBILITIES: "Roles",
        ResponseComponent.RELATED_STANDARDS: "Related Standards",
    },
    ResponseLayoutType.LIST_EXTRACTION: {
        ResponseComponent.DIRECT_LIST: "Direct Answer",
        ResponseComponent.DETAILED_SECTIONS: "Item Descriptions",
        ResponseComponent.INFORMATION: "Source Context",
    },
    ResponseLayoutType.HIERARCHY: {
        ResponseComponent.HIERARCHY_TREE: "Hierarchy",
        ResponseComponent.DETAILED_SECTIONS: "Levels",
    },
}

TEMPLATE_IDS: dict[ResponseLayoutType, str] = {
    ResponseLayoutType.DEFINITION: "definition_v1",
    ResponseLayoutType.WORKFLOW: "workflow_v1",
    ResponseLayoutType.COMPARISON: "comparison_v1",
    ResponseLayoutType.HIERARCHY: "hierarchy_v1",
    ResponseLayoutType.POLICY: "policy_v1",
    ResponseLayoutType.GOVERNANCE: "governance_v1",
    ResponseLayoutType.RELATIONSHIP: "relationship_v1",
    ResponseLayoutType.DECISION_GUIDANCE: "decision_guidance_v1",
    ResponseLayoutType.TROUBLESHOOTING: "troubleshooting_v1",
    ResponseLayoutType.REFERENCE_LOOKUP: "reference_lookup_v1",
    ResponseLayoutType.EXECUTIVE_SUMMARY: "executive_summary_v1",
    ResponseLayoutType.EXECUTIVE_REPORT: "executive_report_v1",
    ResponseLayoutType.COMPLIANCE: "compliance_v1",
    ResponseLayoutType.LONG_REPORT: "long_report_v1",
    ResponseLayoutType.LIST_EXTRACTION: "list_extraction_v1",
    ResponseLayoutType.TIMELINE: "timeline_v1",
    ResponseLayoutType.TABLE_HEAVY: "table_heavy_v1",
    ResponseLayoutType.MIXED: "mixed_v1",
}

# Heading aliases in source answers → component (for reuse of existing sections).
HEADING_ALIASES: dict[str, ResponseComponent] = {
    "executive summary": ResponseComponent.EXECUTIVE_SUMMARY,
    "summary": ResponseComponent.EXECUTIVE_SUMMARY,
    "overview": ResponseComponent.EXECUTIVE_SUMMARY,
    "definition": ResponseComponent.DEFINITION,
    "purpose": ResponseComponent.PURPOSE,
    "key characteristics": ResponseComponent.KEY_CHARACTERISTICS,
    "characteristics": ResponseComponent.KEY_CHARACTERISTICS,
    "important notes": ResponseComponent.IMPORTANT_NOTES,
    "notes": ResponseComponent.IMPORTANT_NOTES,
    "objective": ResponseComponent.OBJECTIVE,
    "workflow steps": ResponseComponent.STEPS,
    "ordered steps": ResponseComponent.STEPS,
    "steps": ResponseComponent.STEPS,
    "roles": ResponseComponent.RESPONSIBILITIES,
    "roles and responsibilities": ResponseComponent.RESPONSIBILITIES,
    "responsibilities": ResponseComponent.RESPONSIBILITIES,
    "outcome": ResponseComponent.OUTCOME,
    "scope": ResponseComponent.SCOPE,
    "requirements": ResponseComponent.REQUIREMENTS,
    "exceptions": ResponseComponent.EXCEPTIONS,
    "governance": ResponseComponent.GOVERNANCE,
    "comparison": ResponseComponent.COMPARISON_TABLE,
    "key differences": ResponseComponent.KEY_DIFFERENCES,
    "recommendations": ResponseComponent.RECOMMENDATIONS,
    "hierarchy": ResponseComponent.HIERARCHY_TREE,
    "levels": ResponseComponent.DETAILED_SECTIONS,
    "relationship": ResponseComponent.RELATIONSHIP_DIAGRAM,
    "how they relate": ResponseComponent.RELATIONSHIP_DIAGRAM,
    "business impact": ResponseComponent.KEY_TAKEAWAYS,
    "business significance": ResponseComponent.KEY_TAKEAWAYS,
    "decision summary": ResponseComponent.DECISION_MATRIX,
    "decision": ResponseComponent.DECISION_MATRIX,
    "criteria": ResponseComponent.DETAILED_SECTIONS,
    "recommended path": ResponseComponent.RECOMMENDATIONS,
    "constraints": ResponseComponent.IMPORTANT_NOTES,
    "next steps": ResponseComponent.KEY_TAKEAWAYS,
    "key findings": ResponseComponent.KEY_TAKEAWAYS,
    "key takeaways": ResponseComponent.KEY_TAKEAWAYS,
    "detailed analysis": ResponseComponent.DETAILED_SECTIONS,
    "related documents": ResponseComponent.RELATED_DOCUMENTS,
    "related standards": ResponseComponent.RELATED_STANDARDS,
    "related policies": ResponseComponent.RELATED_POLICIES,
    "sources": ResponseComponent.SOURCES,
    "timeline": ResponseComponent.TIMELINE,
}


def heading_for(
    layout: ResponseLayoutType,
    component: ResponseComponent,
) -> str:
    overrides = _LAYOUT_HEADING_OVERRIDES.get(layout, {})
    return overrides.get(component) or COMPONENT_HEADINGS.get(
        component, component.value.replace("_", " ").title()
    )


def template_id_for(layout: ResponseLayoutType) -> str:
    return TEMPLATE_IDS.get(layout, f"{layout.value}_v1")
