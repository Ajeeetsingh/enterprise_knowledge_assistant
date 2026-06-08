"""Backward-compatible CLI entry point — delegates to migrated RAG CLI.

Usage:
    python app.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def main() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")
    subprocess.run(
        [sys.executable, "-m", "app.rag.cli"],
        cwd=ROOT / "backend",
        env=env,
        check=False,
    )


if __name__ == "__main__":
    main()
