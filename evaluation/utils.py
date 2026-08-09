"""Shared helpers for the Knowra evaluation utility."""

from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE pairs into ``os.environ`` without overriding existing values."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


def parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None or not str(value).strip():
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def parse_float(value: str | None, *, default: float) -> float:
    if value is None or not str(value).strip():
        return default
    try:
        return float(value)
    except ValueError:
        return default


def parse_int(value: str | None, *, default: int) -> int:
    if value is None or not str(value).strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def read_questions(questions_path: Path) -> list[str]:
    """Read one question per line; ignore blanks and ``#`` comments."""
    if not questions_path.is_file():
        raise FileNotFoundError(f"questions.txt not found: {questions_path}")

    questions: list[str] = []
    for raw_line in questions_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        questions.append(line)
    return questions


def ensure_domain_layout(domain_path: Path) -> None:
    """Ensure the domain folder exists and contains the expected subfolders."""
    if not domain_path.is_dir():
        raise FileNotFoundError(
            f"Domain folder not found: {domain_path}\n"
            f"Create docs/test_docs/<domain_name>/ with questions.txt inside."
        )
    (domain_path / "documents").mkdir(parents=True, exist_ok=True)


def unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = (value or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(text)
    return ordered


def extract_retrieved_documents(api_response: dict[str, Any] | None) -> list[str]:
    """Best-effort document list from a Knowra ``/chat/ask`` response."""
    if not api_response:
        return []
    citations = api_response.get("citations") or []
    sources: list[str] = []
    for citation in citations:
        if isinstance(citation, dict):
            source = citation.get("source")
            if isinstance(source, str):
                sources.append(source)
    return unique_preserve_order(sources)


def extract_retrieved_sources(api_response: dict[str, Any] | None) -> list[str]:
    """Source labels including page when available."""
    if not api_response:
        return []
    citations = api_response.get("citations") or []
    labels: list[str] = []
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        source = citation.get("source")
        if not isinstance(source, str) or not source.strip():
            continue
        page = citation.get("page")
        if isinstance(page, int):
            labels.append(f"{source} (page {page})")
        else:
            labels.append(source)
    return unique_preserve_order(labels)


def extract_final_answer(api_response: dict[str, Any] | None) -> str:
    if not api_response:
        return ""
    answer = api_response.get("answer")
    return answer if isinstance(answer, str) else ""


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def join_list(values: list[str]) -> str:
    return "; ".join(values)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "domain"
