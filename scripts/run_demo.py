"""Run the Enterprise RAG CLI demo."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "app.rag.cli"],
        cwd=ROOT / "backend",
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
