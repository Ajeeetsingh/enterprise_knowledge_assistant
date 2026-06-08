"""Document loading from PDF, TXT, CSV, and JSON sources."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.ingestion.categorizer import resolve_category
from app.ingestion.chunker import DocumentChunk, chunk_text

LOADERS: dict[str, object] = {}


def _load_txt(path: Path, category: str) -> list[DocumentChunk]:
    content = path.read_text(encoding="utf-8")
    return chunk_text(content, path.name, category)


def _load_pdf(path: Path, category: str) -> list[DocumentChunk]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[str] = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())

    content = "\n".join(pages)
    return chunk_text(content, path.name, category)


def _load_csv(path: Path, category: str) -> list[DocumentChunk]:
    rows: list[str] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_text = ", ".join(f"{key}: {value}" for key, value in row.items())
            rows.append(row_text)

    content = "\n".join(rows)
    return chunk_text(content, path.name, category)


def _load_json(path: Path, category: str) -> list[DocumentChunk]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    chunks: list[DocumentChunk] = []

    if isinstance(data, dict):
        summary = data.get("summary")
        if summary:
            chunks.extend(chunk_text(str(summary), path.name, category))

        notes = data.get("notes")
        if notes:
            chunks.extend(chunk_text(str(notes), path.name, category))

        events = data.get("events")
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict):
                    event_text = (
                        f"[{event.get('timestamp', '')}] "
                        f"{event.get('severity', '')} {event.get('event_type', '')}: "
                        f"{event.get('message', '')} "
                        f"(user={event.get('user', '')}, ip={event.get('source_ip', '')})"
                    )
                    chunks.extend(chunk_text(event_text, path.name, category))

        employees = data.get("employees")
        if isinstance(employees, list):
            for employee in employees:
                if isinstance(employee, dict):
                    emp_text = ", ".join(
                        f"{key}: {value}" for key, value in employee.items()
                    )
                    chunks.extend(chunk_text(emp_text, path.name, category))

        if not chunks:
            chunks.extend(chunk_text(json.dumps(data, indent=2), path.name, category))
    else:
        chunks.extend(chunk_text(json.dumps(data, indent=2), path.name, category))

    return chunks


LOADERS.update({
    ".pdf": _load_pdf,
    ".txt": _load_txt,
    ".csv": _load_csv,
    ".json": _load_json,
})


def load_documents(data_dir: str | Path) -> list[DocumentChunk]:
    """Load and chunk all supported documents from a directory."""
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_path}")

    all_chunks: list[DocumentChunk] = []

    for path in sorted(data_path.iterdir()):
        if not path.is_file():
            continue

        loader = LOADERS.get(path.suffix.lower())
        if loader is None:
            continue

        category = resolve_category(path.name)
        all_chunks.extend(loader(path, category))

    return all_chunks
