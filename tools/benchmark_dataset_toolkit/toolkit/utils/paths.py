"""Path helpers for hierarchy-preserving conversion."""

from __future__ import annotations

from pathlib import Path


def relativize_under(path: Path, root: Path) -> Path:
    """Return path relative to root; raise if not nested."""
    return path.resolve().relative_to(root.resolve())


def strip_leading_parts(relative: Path, strip_prefix: str) -> Path:
    """Remove a leading directory segment (e.g. apex_national_bank) if present."""
    if not strip_prefix:
        return relative
    parts = relative.parts
    prefix_parts = Path(strip_prefix).parts
    if len(parts) >= len(prefix_parts) and parts[: len(prefix_parts)] == prefix_parts:
        return Path(*parts[len(prefix_parts) :]) if len(parts) > len(prefix_parts) else Path(".")
    return relative


def map_markdown_to_pdf_target(
    source: Path,
    *,
    input_dir: Path,
    output_dir: Path,
    strip_prefix: str,
) -> tuple[Path, Path]:
    """Map a markdown file to (relative_source, absolute_pdf_target)."""
    relative = relativize_under(source, input_dir)
    # If input_dir is already apex_national_bank, strip_prefix may be a no-op.
    # Also support input_dir = docs/ with strip_prefix = apex_national_bank.
    mapped = strip_leading_parts(relative, strip_prefix)
    if mapped == Path("."):
        mapped = Path(source.name)
    target = (output_dir / mapped).with_suffix(".pdf")
    return relative, target.resolve()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
