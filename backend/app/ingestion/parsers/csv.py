"""CSV document parser."""

from __future__ import annotations

import csv
import io

from app.ingestion.parsers.base import DocumentParser


class CsvParser(DocumentParser):
    """Parse CSV files into a readable text representation."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".csv"})

    def parse(self, content: bytes, filename: str) -> str:
        text = content.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        rows: list[str] = []
        for row in reader:
            rows.append(", ".join(f"{k}: {v}" for k, v in row.items()))
        return "\n".join(rows)
