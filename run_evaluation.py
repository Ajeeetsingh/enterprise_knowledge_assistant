#!/usr/bin/env python3
"""Project-root entrypoint for the standalone Knowra evaluation utility.

Usage:
    python run_evaluation.py human_resources
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def main() -> int:
    evaluation_dir = Path(__file__).resolve().parent / "evaluation"
    target = evaluation_dir / "run_evaluation.py"
    if str(evaluation_dir) not in sys.path:
        sys.path.insert(0, str(evaluation_dir))

    spec = importlib.util.spec_from_file_location("knowra_run_evaluation", target)
    if spec is None or spec.loader is None:
        print(f"Unable to load evaluation entrypoint: {target}")
        return 1

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
