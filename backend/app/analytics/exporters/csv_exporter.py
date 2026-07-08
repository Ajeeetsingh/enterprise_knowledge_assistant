"""CSV exporter for analytics reports (Phase 11.7)."""

from __future__ import annotations

import csv
import io

from app.analytics.services.report_payload import AnalyticsReportPayload, format_report_value


class CSVReportExporter:
    """Export tabular analytics report data as CSV."""

    def export(self, payload: AnalyticsReportPayload) -> bytes:
        """Render *payload* as UTF-8 CSV bytes."""
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["Report Title", payload.module_title])
        writer.writerow(["Generated At", format_report_value(payload.generated_at)])
        writer.writerow(["Start Date", format_report_value(payload.start_date)])
        writer.writerow(["End Date", format_report_value(payload.end_date)])
        writer.writerow([])

        writer.writerow(["KPI Summary"])
        writer.writerow(["Metric", "Value"])
        for label, value in payload.kpis:
            writer.writerow([label, value])
        writer.writerow([])

        for table in payload.tables:
            if not table.headers:
                continue
            writer.writerow([table.name])
            writer.writerow(list(table.headers))
            for row in table.rows:
                writer.writerow(list(row))
            writer.writerow([])

        for trend in payload.trends:
            if not trend.points:
                continue
            writer.writerow([trend.name])
            writer.writerow(["Date", "Value"])
            for date_key, value in sorted(trend.points.items()):
                writer.writerow([date_key, format_report_value(value)])
            writer.writerow([])

        return buffer.getvalue().encode("utf-8")
