#!/usr/bin/env python3
"""Generate the full 100+ case golden evaluation dataset."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.evaluation.dataset.build_golden_dataset import main

if __name__ == "__main__":
    main()
