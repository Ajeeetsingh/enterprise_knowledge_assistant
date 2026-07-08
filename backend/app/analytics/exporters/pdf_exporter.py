"""PDF exporter for analytics reports (Phase 11.7)."""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.analytics.services.report_payload import AnalyticsReportPayload, format_report_value


class PDFReportExporter:
    """Export analytics reports as enterprise PDF documents."""

    def export(self, payload: AnalyticsReportPayload) -> bytes:
        """Render *payload* as PDF bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=f"{payload.module_title} Report",
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor("#111827"),
        )
        section_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontSize=13,
            spaceBefore=12,
            spaceAfter=8,
            textColor=colors.HexColor("#1F2937"),
        )
        body_style = styles["BodyText"]

        story: list = [
            Paragraph(payload.module_title, title_style),
            Paragraph(
                (
                    f"Generated: {format_report_value(payload.generated_at)}<br/>"
                    f"Reporting Period: {format_report_value(payload.start_date)} "
                    f"to {format_report_value(payload.end_date)}"
                ),
                body_style,
            ),
            Spacer(1, 0.2 * inch),
            Paragraph("KPI Summary", section_style),
            self._build_table(
                ["Metric", "Value"],
                [[label, value] for label, value in payload.kpis],
            ),
        ]

        for table in payload.tables:
            if not table.headers:
                continue
            story.extend(
                [
                    Paragraph(table.name, section_style),
                    self._build_table(list(table.headers), [list(row) for row in table.rows]),
                ],
            )

        if payload.trends:
            story.append(Paragraph("Trend Summaries", section_style))
            for trend in payload.trends:
                if not trend.points:
                    continue
                rows = [[date_key, format_report_value(value)] for date_key, value in sorted(trend.points.items())]
                story.extend(
                    [
                        Paragraph(trend.name, body_style),
                        self._build_table(["Date", "Value"], rows),
                        Spacer(1, 0.1 * inch),
                    ],
                )

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def _build_table(headers: list[str], rows: list[list[str]]) -> Table:
        data = [headers, *rows] if rows else [headers, ["No data available", ""]]
        table = Table(data, hAlign="LEFT", repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ],
            ),
        )
        return table
