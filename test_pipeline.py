"""Backward-compatible runner — delegates to migrated test suite.

Usage:
    python test_pipeline.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
TEST_SCRIPT = ROOT / "backend" / "tests" / "rag" / "test_pipeline.py"


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")
    result = subprocess.run(
        [sys.executable, str(TEST_SCRIPT)],
        cwd=ROOT / "backend",
        env=env,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
