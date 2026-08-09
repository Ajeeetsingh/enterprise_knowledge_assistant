"""Intelligent Query Planner pipeline (planning only — never retrieves)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.query_planner.analyzers.constraint_analyzer import ConstraintAnalyzer
from app.query_planner.analyzers.query_analyzer import QueryAnalyzer
from app.query_planner.analyzers.requirement_analyzer import KnowledgeRequirementAnalyzer
from app.query_planner.execution.plan_builder import ExecutionPlanBuilder
from app.query_planner.intent.classifier import IntentClassifier
from app.query_planner.metrics.timing import StageTimer, Stopwatch
from app.query_planner.models.types import QueryExecutionPlan
from app.query_planner.parser.normalizer import QueryNormalizer
from app.query_planner.strategies.builder import StrategyBuilder
from app.query_planner.validators.plan_validator import PlanValidator
from app.query_planner.version import QUERY_PLANNER_PIPELINE_VERSION


class QueryPlanner:
    """
    Understand a query and produce a QueryExecutionPlan.

    Inspects KnowledgeIndexManager for available index names only.
    Never calls FAISS, BM25, or any retriever.
    """

    def __init__(
        self,
        *,
        index_manager: KnowledgeIndexManager | None = None,
        normalizer: QueryNormalizer | None = None,
        classifier: IntentClassifier | None = None,
        query_analyzer: QueryAnalyzer | None = None,
        constraint_analyzer: ConstraintAnalyzer | None = None,
        requirement_analyzer: KnowledgeRequirementAnalyzer | None = None,
        strategy_builder: StrategyBuilder | None = None,
        plan_builder: ExecutionPlanBuilder | None = None,
        validator: PlanValidator | None = None,
    ) -> None:
        self._index_manager = index_manager
        self._normalizer = normalizer or QueryNormalizer()
        self._classifier = classifier or IntentClassifier()
        self._query_analyzer = query_analyzer or QueryAnalyzer()
        self._constraint_analyzer = constraint_analyzer or ConstraintAnalyzer()
        self._requirement_analyzer = requirement_analyzer or KnowledgeRequirementAnalyzer()
        self._strategy_builder = strategy_builder or StrategyBuilder()
        self._plan_builder = plan_builder or ExecutionPlanBuilder()
        self._validator = validator or PlanValidator()
        self._total_timer = StageTimer()
        self._classify_timer = StageTimer()
        self._strategy_timer = StageTimer()
        self._validation_timer = StageTimer()
        self._intent_counts: Counter[str] = Counter()
        self._strategy_counts: Counter[str] = Counter()
        self._unknown_count = 0
        self._plans_generated = 0

    @property
    def version(self) -> str:
        return QUERY_PLANNER_PIPELINE_VERSION

    def plan(self, query: str) -> QueryExecutionPlan:
        total = Stopwatch()
        timeline: dict[str, float] = {}

        stage = Stopwatch()
        normalization = self._normalizer.normalize(query)
        timeline["normalize_ms"] = round(stage.elapsed_ms(), 4)

        stage = Stopwatch()
        intents = self._classifier.classify(normalization)
        classify_ms = stage.elapsed_ms()
        timeline["classify_ms"] = round(classify_ms, 4)
        self._classify_timer.record(classify_ms)

        stage = Stopwatch()
        analysis = self._query_analyzer.analyze(normalization)
        timeline["analyze_ms"] = round(stage.elapsed_ms(), 4)

        stage = Stopwatch()
        constraints = self._constraint_analyzer.extract(normalization, analysis)
        timeline["constraints_ms"] = round(stage.elapsed_ms(), 4)

        stage = Stopwatch()
        required_indexes = self._requirement_analyzer.required_indexes(
            intents, constraints, analysis
        )
        relationship_requirements = self._requirement_analyzer.relationship_requirements(intents)
        timeline["requirements_ms"] = round(stage.elapsed_ms(), 4)

        stage = Stopwatch()
        preferred, fallback, expected = self._strategy_builder.build(
            intents, required_indexes, constraints
        )
        strategy_ms = stage.elapsed_ms()
        timeline["strategy_ms"] = round(strategy_ms, 4)
        self._strategy_timer.record(strategy_ms)

        available = set(self._index_manager.indexes.keys()) if self._index_manager else None

        plan = self._plan_builder.build(
            raw_query=query,
            normalization=normalization,
            intents=intents,
            analysis=analysis,
            constraints=constraints,
            required_indexes=required_indexes,
            relationship_requirements=relationship_requirements,
            preferred_strategy=preferred,
            fallback_strategy=fallback,
            expected_output=expected,
            available_indexes=available,
            timeline_ms=timeline,
        )

        stage = Stopwatch()
        self._validator.validate(plan)
        validation_ms = stage.elapsed_ms()
        timeline["validation_ms"] = round(validation_ms, 4)
        plan.diagnostics.timeline_ms = timeline
        self._validation_timer.record(validation_ms)

        total_ms = total.elapsed_ms()
        timeline["total_ms"] = round(total_ms, 4)
        plan.diagnostics.timeline_ms = timeline
        self._total_timer.record(total_ms)

        self._plans_generated += 1
        self._intent_counts[plan.primary_intent] += 1
        self._strategy_counts[plan.preferred_strategy] += 1
        if plan.primary_intent == "UNKNOWN":
            self._unknown_count += 1
        return plan

    def statistics(self) -> dict[str, Any]:
        return {
            "queries_analyzed": self._plans_generated,
            "average_planning_time_ms": round(self._total_timer.average_ms, 4),
            "classification_latency_ms": round(self._classify_timer.average_ms, 4),
            "strategy_latency_ms": round(self._strategy_timer.average_ms, 4),
            "validation_latency_ms": round(self._validation_timer.average_ms, 4),
            "intent_distribution": dict(self._intent_counts),
            "strategy_distribution": dict(self._strategy_counts),
            "unknown_queries": self._unknown_count,
            "planner_version": self.version,
        }
