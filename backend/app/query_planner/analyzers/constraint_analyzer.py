"""Constraint extraction from natural-language queries."""

from __future__ import annotations

import re

from app.query_planner.analyzers.query_analyzer import QueryAnalysis
from app.query_planner.models.types import QueryConstraints
from app.query_planner.parser.normalizer import NormalizationResult


class ConstraintAnalyzer:
    def extract(
        self,
        normalization: NormalizationResult,
        analysis: QueryAnalysis,
    ) -> QueryConstraints:
        lower = normalization.normalized.lower()
        constraints = QueryConstraints(
            latest=bool(re.search(r"\blatest\b|\bmost recent\b|\bcurrent\b", lower)),
            oldest=bool(re.search(r"\boldest\b|\bearliest\b|\bfirst version\b", lower)),
            department=analysis.departments[0] if analysis.departments else None,
            collection=analysis.collections[0] if analysis.collections else None,
            document_type=analysis.filters.get("document_type"),
            entity_filters=[
                entity.text for entity in analysis.entities if entity.kind == "entity"
            ],
            taxonomy_path=analysis.taxonomy_paths[0] if analysis.taxonomy_paths else None,
        )

        before = re.search(r"\bbefore\s+(\d{4}(?:[-/]\d{1,2}[-/]\d{1,2})?)", lower)
        after = re.search(r"\bafter\s+(\d{4}(?:[-/]\d{1,2}[-/]\d{1,2})?)", lower)
        if before:
            constraints.before = before.group(1)
        if after:
            constraints.after = after.group(1)

        lang = re.search(r"\b(?:in|language)\s+(english|spanish|french|german|hindi)\b", lower)
        if lang:
            constraints.language = lang.group(1)

        if analysis.document_names:
            name = analysis.document_names[0]
            if " " not in name and "." in name:
                constraints.exact_filename = name
            else:
                constraints.partial_filename = name
        elif "partial_filename" in analysis.filters:
            constraints.partial_filename = analysis.filters["partial_filename"]

        if analysis.versions:
            # Prefer explicit version labels over latest/oldest flags when present.
            non_flag = [v for v in analysis.versions if v not in {"latest", "oldest"}]
            if non_flag:
                constraints.version_label = non_flag[0]

        return constraints
