"""RAG observability — diagnostics only; never changes ranking or answers."""

from app.rag.observability.collector import (
    RagTraceSession,
    finish_trace,
    get_active_trace,
    is_diagnostics_enabled,
    start_trace,
    trace_question,
)
from app.rag.observability.reporter import render_diagnostic_report, write_diagnostic_report

__all__ = [
    "RagTraceSession",
    "finish_trace",
    "get_active_trace",
    "is_diagnostics_enabled",
    "render_diagnostic_report",
    "start_trace",
    "trace_question",
    "write_diagnostic_report",
]
