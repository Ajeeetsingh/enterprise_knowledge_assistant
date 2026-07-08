"""Administrator knowledge analytics API (Phase 11.4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.analytics.analytics_dependencies import (
    get_knowledge_analytics_service,
    parse_analytics_filter,
    resolve_analytics_context,
    resolve_user_list_limit,
)
from app.analytics.context import AnalyticsContext
from app.analytics.schemas.filters import AnalyticsFilter
from app.analytics.schemas.knowledge import (
    CollectionAnalyticsResponse,
    DocumentAnalyticsResponse,
    FreshnessAnalyticsResponse,
    KnowledgeGapResponse,
    KnowledgeOverviewResponse,
    SearchAnalyticsResponse,
)
from app.analytics.services.knowledge_analytics_service import KnowledgeAnalyticsService
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
    response_model=KnowledgeOverviewResponse,
    summary="Get knowledge analytics overview",
    description=(
        "Return administrator KPIs for knowledge base health including document "
        "inventory, usage, and search success metrics."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_knowledge_overview(
    _: User = Depends(require_audit_admin),
    service: KnowledgeAnalyticsService = Depends(get_knowledge_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> KnowledgeOverviewResponse:
    """Return knowledge analytics KPI summary."""
    return KnowledgeOverviewResponse.from_snapshot(service.get_overview(context))


@router.get(
    "/documents",
    response_model=DocumentAnalyticsResponse,
    summary="Get document usage analytics",
    description=(
        "Return most and least viewed documents, citation averages, and "
        "document usage trends for the selected reporting window."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_document_analytics(
    _: User = Depends(require_audit_admin),
    service: KnowledgeAnalyticsService = Depends(get_knowledge_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> DocumentAnalyticsResponse:
    """Return document usage analytics."""
    limit = resolve_user_list_limit(filters)
    return DocumentAnalyticsResponse.from_snapshot(
        service.get_documents(context, limit=limit, offset=filters.offset),
    )


@router.get(
    "/collections",
    response_model=CollectionAnalyticsResponse,
    summary="Get collection analytics",
    description=(
        "Return collection popularity, document counts, usage, and retrieval "
        "distribution for the selected reporting window."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_collection_analytics(
    _: User = Depends(require_audit_admin),
    service: KnowledgeAnalyticsService = Depends(get_knowledge_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> CollectionAnalyticsResponse:
    """Return collection analytics."""
    limit = resolve_user_list_limit(filters)
    return CollectionAnalyticsResponse.from_snapshot(
        service.get_collections(context, limit=limit, offset=filters.offset),
    )


@router.get(
    "/searches",
    response_model=SearchAnalyticsResponse,
    summary="Get search analytics",
    description=(
        "Return search topics, document and collection search activity, success "
        "rates, and search trends for the selected reporting window."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_search_analytics(
    _: User = Depends(require_audit_admin),
    service: KnowledgeAnalyticsService = Depends(get_knowledge_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> SearchAnalyticsResponse:
    """Return search behavior analytics."""
    limit = resolve_user_list_limit(filters)
    return SearchAnalyticsResponse.from_snapshot(
        service.get_searches(context, limit=limit, offset=filters.offset),
    )


@router.get(
    "/gaps",
    response_model=KnowledgeGapResponse,
    summary="Get knowledge gap analytics",
    description=(
        "Return measurable knowledge gap facts such as unanswered questions, "
        "uncited documents, and low-engagement collections."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_knowledge_gap_analytics(
    _: User = Depends(require_audit_admin),
    service: KnowledgeAnalyticsService = Depends(get_knowledge_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> KnowledgeGapResponse:
    """Return knowledge gap analytics."""
    limit = resolve_user_list_limit(filters)
    return KnowledgeGapResponse.from_snapshot(
        service.get_gaps(context, limit=limit, offset=filters.offset),
    )


@router.get(
    "/freshness",
    response_model=FreshnessAnalyticsResponse,
    summary="Get content freshness analytics",
    description=(
        "Return recently uploaded and updated documents, oldest content, "
        "longest inactive documents, and upload trends."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_freshness_analytics(
    _: User = Depends(require_audit_admin),
    service: KnowledgeAnalyticsService = Depends(get_knowledge_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> FreshnessAnalyticsResponse:
    """Return content freshness analytics."""
    limit = resolve_user_list_limit(filters)
    return FreshnessAnalyticsResponse.from_snapshot(
        service.get_freshness(context, limit=limit, offset=filters.offset),
    )
