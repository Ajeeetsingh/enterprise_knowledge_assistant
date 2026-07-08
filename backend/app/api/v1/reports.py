"""Administrator reporting and export API (Phase 11.7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import ValidationError

from app.analytics.analytics_dependencies import get_reporting_service
from app.analytics.schemas.filters import AnalyticsFilter
from app.analytics.schemas.reporting import (
    ReportExportRequest,
    ReportFormatResponse,
    ReportFormatsResponse,
    ReportModuleResponse,
    ReportModulesResponse,
)
from app.analytics.services.reporting_service import ReportingService
from app.analytics.utils.date_filters import context_from_filter
from app.auth.dependencies import require_audit_admin
from app.db.models import User
from app.schemas.errors import ErrorResponse

router = APIRouter()

_REPORT_ERROR_RESPONSES: dict[int, dict[str, object]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token.",
    },
    403: {
        "model": ErrorResponse,
        "description": "Only administrators may export analytics reports.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Invalid report export parameters.",
    },
}


@router.get(
    "/modules",
    response_model=ReportModulesResponse,
    summary="List exportable analytics modules",
    responses=_REPORT_ERROR_RESPONSES,
)
def list_report_modules(
    _: User = Depends(require_audit_admin),
    service: ReportingService = Depends(get_reporting_service),
) -> ReportModulesResponse:
    """Return analytics modules available for export."""
    items = [
        ReportModuleResponse(
            id=module.id.value,
            title=module.title,
            description=module.description,
        )
        for module in service.list_modules()
    ]
    return ReportModulesResponse(items=items)


@router.get(
    "/formats",
    response_model=ReportFormatsResponse,
    summary="List supported report export formats",
    responses=_REPORT_ERROR_RESPONSES,
)
def list_report_formats(
    _: User = Depends(require_audit_admin),
    service: ReportingService = Depends(get_reporting_service),
) -> ReportFormatsResponse:
    """Return supported export formats."""
    items = [
        ReportFormatResponse(
            id=report_format.id.value,
            label=report_format.label,
            media_type=report_format.media_type,
            extension=report_format.extension,
        )
        for report_format in service.list_formats()
    ]
    return ReportFormatsResponse(items=items)


@router.post(
    "/export",
    summary="Export analytics report",
    description=(
        "Generate and download an analytics report for the selected module, "
        "date range, and file format."
    ),
    responses={
        **_REPORT_ERROR_RESPONSES,
        200: {
            "content": {
                "text/csv": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
                "application/pdf": {},
            },
            "description": "Generated report file.",
        },
    },
)
def export_report(
    request: ReportExportRequest,
    _: User = Depends(require_audit_admin),
    service: ReportingService = Depends(get_reporting_service),
) -> Response:
    """Export analytics data for operational and compliance reporting."""
    try:
        filters = AnalyticsFilter(
            range_preset=request.date_range,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        context = context_from_filter(filters, default_days=7)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid report export parameters.") from exc

    result = service.export_report(
        module=request.module,
        report_format=request.format,
        context=context,
    )
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
        },
    )
