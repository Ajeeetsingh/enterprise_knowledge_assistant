"""XLSX document parser."""

from __future__ import annotations

from app.core.exceptions import DocumentIngestionError
from app.ingestion.parsers.base import DocumentParser


class XlsxParser(DocumentParser):
    """Extract text from Excel .xlsx files using openpyxl."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".xlsx"})

    def parse(self, content: bytes, filename: str) -> str:
        try:
            import openpyxl
        except ImportError as exc:
            raise DocumentIngestionError(
                "openpyxl is required for XLSX parsing. "
                "Install it with: pip install openpyxl"
            ) from exc

        import io

        workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        rows: list[str] = []
        for sheet in workbook.worksheets:
            for row in sheet.iter_rows(values_only=True):
                cells = [str(cell) for cell in row if cell is not None]
                if cells:
                    rows.append(", ".join(cells))
        return "\n".join(rows)
