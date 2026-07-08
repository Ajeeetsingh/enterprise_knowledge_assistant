"""Administrator AI analytics API (Phase 11.3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.analytics.analytics_dependencies import (
    get_ai_analytics_service,
    parse_analytics_filter,
    resolve_analytics_context,
    resolve_user_list_limit,
)
from app.analytics.context import AnalyticsContext
from app.analytics.schemas.ai import (
    AIFailuresResponse,
    AIAnalyticsOverviewResponse,
    AIQuestionsResponse,
    AIRetrievalResponse,
    AITrendsResponse,
    FailureAnalysisItemResponse,
    QuestionFrequencyItemResponse,
)
from app.analytics.schemas.filters import AnalyticsFilter
from app.analytics.services.ai_analytics_service import AIAnalyticsService
from app.auth.dependencies import require_audit_admin
from app.db.models import User
from app.schemas.errors import ErrorResponse

router = APIRouter()

_ANALYTICS_ERROR_RESPONSES: dict[int, dict[str, object]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token.",
    },
    403: {
        "model": ErrorResponse,
        "description": "Only administrators may access analytics data.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Invalid analytics parameters.",
    },
}


@router.get(
    "/overview",
    response_model=AIAnalyticsOverviewResponse,
    summary="Get AI analytics overview",
    description=(
        "Return administrator KPIs for AI assistant performance including "
        "response volume, retrieval success, and confidence metrics."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_ai_analytics_overview(
    _: User = Depends(require_audit_admin),
    service: AIAnalyticsService = Depends(get_ai_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> AIAnalyticsOverviewResponse:
    """Return AI analytics KPI summary."""
    return AIAnalyticsOverviewResponse.from_snapshot(service.get_overview(context))


@router.get(
    "/trends",
    response_model=AITrendsResponse,
    summary="Get AI performance trends",
    description=(
        "Return time-series data for questions, responses, retrieval outcomes, "
        "response time, and citation usage."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_ai_trends(
    _: User = Depends(require_audit_admin),
    service: AIAnalyticsService = Depends(get_ai_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> AITrendsResponse:
    """Return AI performance trend series."""
    return AITrendsResponse.from_snapshot(service.get_trends(context))


@router.get(
    "/retrieval",
    response_model=AIRetrievalResponse,
    summary="Get retrieval analytics",
    description=(
        "Return retrieval success, empty retrieval counts, and citation source "
        "distribution for the selected reporting window."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_retrieval_analytics(
    _: User = Depends(require_audit_admin),
    service: AIAnalyticsService = Depends(get_ai_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> AIRetrievalResponse:
    """Return retrieval analytics summary."""
    return AIRetrievalResponse.from_snapshot(service.get_retrieval(context))


@router.get(
    "/questions",
    response_model=AIQuestionsResponse,
    summary="Get AI question quality analytics",
    description=(
        "Return recurring user questions and response quality metrics for the "
        "selected reporting window."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_ai_question_analytics(
    _: User = Depends(require_audit_admin),
    service: AIAnalyticsService = Depends(get_ai_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> AIQuestionsResponse:
    """Return AI question quality analytics."""
    limit = resolve_user_list_limit(filters)
    snapshot = service.get_questions(context, limit=limit, offset=filters.offset)
    return AIQuestionsResponse(
        items=[
            QuestionFrequencyItemResponse(
                question=str(item["question"]),
                count=int(item["count"]),
            )
            for item in snapshot.items
        ],
        total=snapshot.total,
        average_citations_per_response=snapshot.average_citations_per_response,
        responses_without_citations=snapshot.responses_without_citations,
        questions_without_documents=snapshot.questions_without_documents,
        quality_summary=snapshot.quality_summary,
        start_date=snapshot.start_date,
        end_date=snapshot.end_date,
    )


@router.get(
    "/failures",
    response_model=AIFailuresResponse,
    summary="Get AI failure analytics",
    description=(
        "Return aggregated retrieval failure reasons for the selected "
        "reporting window."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_ai_failure_analytics(
    _: User = Depends(require_audit_admin),
    service: AIAnalyticsService = Depends(get_ai_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> AIFailuresResponse:
    """Return AI failure analytics."""
    limit = resolve_user_list_limit(filters)
    snapshot = service.get_failures(context, limit=limit, offset=filters.offset)
    return AIFailuresResponse(
        items=[
            FailureAnalysisItemResponse(
                reason=str(item["reason"]),
                count=int(item["count"]),
            )
            for item in snapshot.items
        ],
        total=snapshot.total,
        limit=snapshot.limit,
        offset=snapshot.offset,
        start_date=snapshot.start_date,
        end_date=snapshot.end_date,
    )
