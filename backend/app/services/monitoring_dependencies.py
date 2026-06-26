"""FastAPI dependencies for monitoring and metrics (Phase 7.7)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.metrics_service import MetricsService, build_metrics_service
from app.services.monitoring_service import MonitoringService, build_monitoring_service


def get_monitoring_service(db: Session = Depends(get_db)) -> MonitoringService:
    """Return a monitoring service bound to the current database session."""
    return build_monitoring_service(db)


def get_metrics_service() -> MetricsService:
    """Return a stateless metrics service."""
    return build_metrics_service()
