"""One-command setup for local manual testing.

Usage:
    python scripts/setup_manual_testing.py
    python scripts/setup_manual_testing.py --skip-chat

Runs ``seed_database.py --all`` (roles, admin, demo users, demo data).

Does not start Docker, run migrations, or launch servers — see
docs/TESTING.md and docs/DEVELOPMENT.md for the full workflow.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-chat",
        action="store_true",
        help="Pass --skip-chat to demo data seeding (faster, no embedding model).",
    )
    parser.add_argument(
        "--analytics-only",
        action="store_true",
        help="Pass --analytics-only to demo data seeding.",
    )
    args = parser.parse_args()

    cmd = [sys.executable, str(SCRIPTS / "seed_database.py"), "--all"]
    if args.skip_chat:
        cmd.append("--skip-chat")
    if args.analytics_only:
        cmd.append("--analytics-only")

    print(f"\n==> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode != 0:
        return result.returncode

    print("\nManual testing setup complete.")
    print("Next: start backend + frontend and follow docs/DEVELOPMENT.md / docs/TESTING.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
