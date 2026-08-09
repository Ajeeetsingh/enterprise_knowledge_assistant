"""Unified database seeding utility."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed database roles, users, and demo data.")
    parser.add_argument("--admin", action="store_true", help="Seed admin user (requires roles).")
    parser.add_argument("--roles", action="store_true", help="Seed default roles.")
    parser.add_argument(
        "--domains",
        action="store_true",
        help="Seed default knowledge domains.",
    )
    parser.add_argument("--demo", action="store_true", help="Seed demo users and sample data.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Seed roles, knowledge domains, admin, demo users, and demo data.",
    )
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
    args = parser.parse_args(argv)

    if args.all:
        steps = ["roles", "domains", "admin", "demo_users", "demo_data"]
    else:
        steps = []
        if args.roles:
            steps.append("roles")
        if args.domains:
            steps.append("domains")
        if args.admin:
            steps.append("admin")
        if args.demo:
            steps.extend(["demo_users", "demo_data"])
        if not steps:
            parser.error("Specify --roles, --domains, --admin, --demo, or --all")

    from seeding import admin, demo_data, demo_users, knowledge_domains, roles

    runners = {
        "roles": roles.seed_roles,
        "domains": knowledge_domains.seed_knowledge_domains,
        "admin": admin.seed_admin_user,
        "demo_users": demo_users.seed_demo_users,
    }

    exit_code = 0
    for step in steps:
        print(f"\n==> {step}")
        if step == "demo_data":
            if args.skip_chat and args.analytics_only:
                print("Error: --skip-chat and --analytics-only cannot be used together.")
                return 1
            code = demo_data.seed_demo_data(
                skip_chat=args.skip_chat,
                analytics_only=args.analytics_only,
            )
        else:
            code = runners[step]()
        if code != 0:
            exit_code = code
            break

    if exit_code == 0:
        print("\nDatabase seeding complete.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
