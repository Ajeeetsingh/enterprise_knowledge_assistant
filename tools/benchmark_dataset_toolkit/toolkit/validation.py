"""Post-conversion artefact validation."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF"


def is_readable_pdf(path: Path, *, min_bytes: int = 64, check_magic: bool = True) -> tuple[bool, str]:
    """Return (ok, reason)."""
    if not path.exists():
        return False, "file does not exist"
    if not path.is_file():
        return False, "path is not a file"
    try:
        size = path.stat().st_size
    except OSError as exc:
        return False, f"stat failed: {exc}"
    if size < min_bytes:
        return False, f"file too small ({size} bytes)"
    try:
        with path.open("rb") as fh:
            header = fh.read(5)
            # Touch more bytes to ensure readability
            fh.seek(0, 2)
            _ = fh.tell()
    except OSError as exc:
        return False, f"unreadable: {exc}"
    if check_magic and not header.startswith(PDF_MAGIC):
        return False, f"missing PDF magic header (got {header!r})"
    return True, "ok"


def verify_pdf(path: Path, *, min_bytes: int = 64, check_magic: bool = True) -> bool:
    ok, reason = is_readable_pdf(path, min_bytes=min_bytes, check_magic=check_magic)
    if not ok:
        logger.error("PDF verification failed for %s: %s", path, reason)
    return ok
