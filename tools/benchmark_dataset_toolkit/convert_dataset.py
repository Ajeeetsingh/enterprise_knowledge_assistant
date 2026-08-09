#!/usr/bin/env python3
"""Knowra Benchmark Dataset Toolkit — CLI entry point.

Examples
--------
    python convert_dataset.py
    python convert_dataset.py --force
    python convert_dataset.py --workers 8
    python convert_dataset.py --input docs/apex_national_bank
    python convert_dataset.py --output benchmark/pdf
    python convert_dataset.py --dry-run
    python convert_dataset.py --verbose
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python convert_dataset.py` without installing the package.
_TOOLKIT_HOME = Path(__file__).resolve().parent
if str(_TOOLKIT_HOME) not in sys.path:
    sys.path.insert(0, str(_TOOLKIT_HOME))

from toolkit.cli import main  # noqa: E402


if __name__ == "__main__":
    main(standalone_mode=True)
