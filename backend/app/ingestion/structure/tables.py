"""Table region detection without flattening."""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass

from app.ingestion.structure.config import StructureExtractionSettings
from app.ingestion.structure.line_stream import AnnotatedLine

_SENTENCE_END_RE = re.compile(r"[.!?]")
_PUNCTUATION_RE = re.compile(r"[,.;:!?]")
_NUMERIC_CELL_RE = re.compile(r"\d")
_COVER_METADATA_MARKERS = (
    "document id",
    "version",
    "classification",
    "approved by",
    "effective date",
    "document control",
    "confidential",
    "internal use only",
    "owner",
    "gtfs-",
)
_TITLE_PAGE_MARKERS = (
    "company overview",
    "trusted.",
    "innovative.",
    "corporate profile",
    "executive budget",
    "quarterly financial report",
    "employee handbook",
)


@dataclass
class DetectedTable:
    """A detected table region in the line stream."""

    start_line_index: int
    end_line_index: int
    headers: list[str]
    rows: list[list[str]]
    page_start: int | None
    page_end: int | None
    confidence: float = 0.0


@dataclass(frozen=True)
class _TableCandidate:
    table: DetectedTable
    confidence: float


def _split_columns(line: str, min_gap: int) -> list[str] | None:
    pattern = re.compile(rf"\s{{{min_gap},}}")
    parts = [part.strip() for part in pattern.split(line.strip()) if part.strip()]
    if len(parts) >= 2:
        return parts
    return None


def _is_probable_header_cell(text: str) -> bool:
    if not text or len(text) > 50:
        return False
    if ";" in text and len(text) > 30:
        return False
    if text.endswith(".") and len(text.split()) > 6:
        return False
    return True


def _is_probable_table_data_line(text: str) -> bool:
    if len(text) > 120:
        return False
    if text.count(". ") >= 2 and len(text.split()) > 18:
        return False
    return True


def _punctuation_density(text: str) -> float:
    if not text:
        return 0.0
    return len(_PUNCTUATION_RE.findall(text)) / len(text)


def _is_sentence_like(text: str) -> bool:
    if len(text) > 100:
        return True
    if text.count(". ") >= 2:
        return True
    if _SENTENCE_END_RE.search(text) and len(text.split()) > 12:
        return True
    return False


def _header_likeness(text: str) -> float:
    if not text:
        return 0.0
    score = 1.0
    if len(text) > 50:
        score -= 0.4
    if _is_sentence_like(text):
        score -= 0.5
    if _punctuation_density(text) > 0.08:
        score -= 0.3
    if len(text.split()) > 8:
        score -= 0.2
    return max(0.0, score)


def _is_cover_metadata(headers: list[str], rows: list[list[str]]) -> bool:
    blob = " ".join(headers + [cell for row in rows for cell in row]).lower()
    hits = sum(1 for marker in _COVER_METADATA_MARKERS if marker in blob)
    return hits >= 2


def _is_title_page_content(headers: list[str], rows: list[list[str]], page_start: int | None) -> bool:
    if page_start not in {None, 1}:
        return False
    blob = " ".join(headers + [cell for row in rows for cell in row]).lower()
    return any(marker in blob for marker in _TITLE_PAGE_MARKERS)


def _column_alignment_score(headers: list[str], rows: list[list[str]]) -> float:
    if not rows:
        return 0.0
    column_count = len(headers)
    scores: list[float] = []
    for column_index in range(column_count):
        lengths = [len(row[column_index]) for row in rows if len(row) > column_index]
        if len(lengths) < 2:
            scores.append(0.5)
            continue
        mean_length = statistics.mean(lengths)
        if mean_length == 0:
            scores.append(1.0)
            continue
        stdev = statistics.pstdev(lengths)
        coefficient = stdev / mean_length
        if coefficient <= 0.35:
            scores.append(1.0)
        elif coefficient <= 0.7:
            scores.append(0.6)
        else:
            scores.append(0.2)
    return statistics.mean(scores) if scores else 0.0


def _row_structure_score(rows: list[list[str]]) -> float:
    if len(rows) < 2:
        return 0.5
    word_counts = [sum(len(cell.split()) for cell in row) for row in rows]
    if max(word_counts) == 0:
        return 0.5
    if statistics.mean(word_counts) == 0:
        return 0.5
    stdev = statistics.pstdev(word_counts)
    mean_words = statistics.mean(word_counts)
    coefficient = stdev / mean_words
    if coefficient <= 0.45:
        return 1.0
    if coefficient <= 0.9:
        return 0.6
    return 0.2


def _tabular_numeric_pattern_score(rows: list[list[str]]) -> float:
    cells = [cell for row in rows for cell in row]
    if not cells:
        return 0.0
    numeric_cells = sum(1 for cell in cells if _NUMERIC_CELL_RE.search(cell))
    ratio = numeric_cells / len(cells)
    if ratio >= 0.35:
        return 1.0
    if ratio >= 0.15:
        return 0.6
    return 0.0


def _narrative_penalty(cells: list[str]) -> float:
    narrative_cells = sum(
        1
        for cell in cells
        if (";" in cell and len(cell) > 35)
        or (" while " in cell.lower() and len(cell) > 60)
        or (" reflects " in cell.lower())
    )
    if not cells:
        return 0.0
    ratio = narrative_cells / len(cells)
    if ratio >= 0.20:
        return 0.35
    if ratio >= 0.10:
        return 0.18
    return 0.0


def _prose_penalty(cells: list[str]) -> float:
    if not cells:
        return 0.0
    long_cells = sum(1 for cell in cells if len(cell) > 80)
    sentence_cells = sum(1 for cell in cells if _is_sentence_like(cell))
    long_ratio = long_cells / len(cells)
    sentence_ratio = sentence_cells / len(cells)
    penalty = 0.0
    if long_ratio >= 0.25:
        penalty += 0.25
    if sentence_ratio >= 0.20:
        penalty += 0.30
    if sentence_ratio >= 0.40:
        penalty += 0.20
    return penalty


def _punctuation_penalty(cells: list[str]) -> float:
    if not cells:
        return 0.0
    densities = [_punctuation_density(cell) for cell in cells]
    high = sum(1 for density in densities if density > 0.06)
    ratio = high / len(cells)
    if ratio >= 0.35:
        return 0.25
    if ratio >= 0.20:
        return 0.12
    return 0.0


def _row_width_variance_penalty(rows: list[list[str]]) -> float:
    if len(rows) < 2:
        return 0.0
    widths = [sum(len(cell) for cell in row) for row in rows]
    mean_width = statistics.mean(widths)
    if mean_width == 0:
        return 0.0
    stdev = statistics.pstdev(widths)
    coefficient = stdev / mean_width
    if coefficient >= 1.0:
        return 0.20
    if coefficient >= 0.7:
        return 0.10
    return 0.0


def score_table_candidate(
    headers: list[str],
    rows: list[list[str]],
    *,
    page_start: int | None,
    settings: StructureExtractionSettings,
) -> float:
    """Score how likely a header/row block is a real table (0.0–1.0)."""
    if len(headers) < settings.min_table_columns or len(rows) < settings.min_table_rows:
        return 0.0

    all_cells = headers + [cell for row in rows for cell in row]
    avg_cell_len = statistics.mean(len(cell) for cell in all_cells)

    score = 0.0

    # Rewards
    header_score = statistics.mean(_header_likeness(header) for header in headers)
    score += 0.22 * header_score

    if avg_cell_len <= 28:
        score += 0.20
    elif avg_cell_len <= 45:
        score += 0.15
    elif avg_cell_len <= 70:
        score += 0.08
    else:
        score -= 0.10

    score += 0.18 * _column_alignment_score(headers, rows)
    score += 0.15 * _row_structure_score(rows)
    score += 0.10 * _tabular_numeric_pattern_score(rows)

    if all(len(row) == len(headers) for row in rows):
        score += 0.10

    # Penalties
    score -= _prose_penalty(all_cells)
    score -= _narrative_penalty(all_cells)
    score -= _punctuation_penalty(all_cells)
    score -= _row_width_variance_penalty(rows)

    if _is_cover_metadata(headers, rows):
        score -= 0.45
    if _is_title_page_content(headers, rows, page_start):
        score -= 0.25

    oversized_rows = sum(1 for row in rows if sum(len(cell) for cell in row) > 220)
    if oversized_rows / len(rows) >= 0.30:
        score -= 0.20

    return max(0.0, min(1.0, score))


def _accept_candidate(
    candidate: DetectedTable,
    settings: StructureExtractionSettings,
) -> bool:
    return candidate.confidence >= settings.table_confidence_threshold


def _detect_gap_tables(
    lines: list[AnnotatedLine],
    consumed: set[int],
    settings: StructureExtractionSettings,
) -> list[DetectedTable]:
    tables: list[DetectedTable] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.is_blank or line.index in consumed:
            index += 1
            continue

        columns = _split_columns(line.text, settings.table_column_gap_spaces)
        if columns is None:
            index += 1
            continue

        column_count = len(columns)
        block_lines = [line]
        row_values = [columns]
        scan = index + 1
        while scan < len(lines):
            candidate = lines[scan]
            if candidate.is_blank:
                break
            if candidate.index in consumed:
                break
            next_columns = _split_columns(candidate.text, settings.table_column_gap_spaces)
            if next_columns is None or len(next_columns) != column_count:
                break
            block_lines.append(candidate)
            row_values.append(next_columns)
            scan += 1

        if len(row_values) >= settings.min_table_rows:
            headers = row_values[0]
            rows = row_values[1:]
            if all(_is_probable_header_cell(cell) for cell in headers):
                confidence = score_table_candidate(
                    headers,
                    rows,
                    page_start=block_lines[0].page,
                    settings=settings,
                )
                candidate = DetectedTable(
                    start_line_index=block_lines[0].index,
                    end_line_index=block_lines[-1].index,
                    headers=headers,
                    rows=rows,
                    page_start=block_lines[0].page,
                    page_end=block_lines[-1].page,
                    confidence=confidence,
                )
                if _accept_candidate(candidate, settings):
                    tables.append(candidate)
                    consumed.update(item.index for item in block_lines)
                    index = scan
                    continue
        index += 1
    return tables


def _build_stacked_candidate(
    lines: list[AnnotatedLine],
    index: int,
    column_count: int,
    consumed: set[int],
    settings: StructureExtractionSettings,
) -> _TableCandidate | None:
    if index + column_count > len(lines):
        return None

    header_candidates = lines[index : index + column_count]
    if any(line.is_blank or line.index in consumed for line in header_candidates):
        return None
    if not all(_is_probable_header_cell(line.text) for line in header_candidates):
        return None

    headers = [line.text.strip() for line in header_candidates]
    data_lines: list[AnnotatedLine] = []
    scan = index + column_count
    max_data_lines = column_count * settings.max_stacked_table_rows

    while scan < len(lines):
        candidate = lines[scan]
        if candidate.is_blank or candidate.index in consumed:
            break
        if len(candidate.text) > 120 or not _is_probable_table_data_line(candidate.text):
            break
        data_lines.append(candidate)
        scan += 1
        if len(data_lines) >= max_data_lines:
            break

    if len(data_lines) < column_count:
        return None

    rows: list[list[str]] = []
    for row_start in range(0, len(data_lines), column_count):
        chunk = data_lines[row_start : row_start + column_count]
        if len(chunk) != column_count:
            rows = []
            break
        rows.append([item.text.strip() for item in chunk])

    if len(rows) < settings.min_table_rows:
        return None

    confidence = score_table_candidate(
        headers,
        rows,
        page_start=header_candidates[0].page,
        settings=settings,
    )
    all_lines = header_candidates + data_lines[: len(rows) * column_count]
    table = DetectedTable(
        start_line_index=all_lines[0].index,
        end_line_index=all_lines[-1].index,
        headers=headers,
        rows=rows,
        page_start=all_lines[0].page,
        page_end=all_lines[-1].page,
        confidence=confidence,
    )
    return _TableCandidate(table=table, confidence=confidence)


def _detect_confidence_stacked_tables(
    lines: list[AnnotatedLine],
    consumed: set[int],
    settings: StructureExtractionSettings,
) -> list[DetectedTable]:
    """Detect stacked-row tables using confidence scoring instead of width maximization."""
    tables: list[DetectedTable] = []
    index = 0
    max_columns = settings.max_table_columns

    while index < len(lines):
        best: _TableCandidate | None = None

        for column_count in range(settings.min_table_columns, max_columns + 1):
            candidate = _build_stacked_candidate(
                lines,
                index,
                column_count,
                consumed,
                settings,
            )
            if candidate is None:
                continue
            if best is None or candidate.confidence > best.confidence:
                best = candidate

        if best is not None and _accept_candidate(best.table, settings):
            tables.append(best.table)
            for line in lines:
                if best.table.start_line_index <= line.index <= best.table.end_line_index:
                    consumed.add(line.index)
            index = best.table.end_line_index + 1
            continue
        index += 1
    return tables


def detect_tables(
    lines: list[AnnotatedLine],
    settings: StructureExtractionSettings,
) -> list[DetectedTable]:
    """Detect table regions while preserving rows, columns, and headers."""
    consumed: set[int] = set()
    tables = _detect_gap_tables(lines, consumed, settings)
    tables.extend(_detect_confidence_stacked_tables(lines, consumed, settings))
    tables.sort(key=lambda table: table.start_line_index)
    return tables
