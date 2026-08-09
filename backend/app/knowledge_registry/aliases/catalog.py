"""Canonical concept catalog and alias map (extensible)."""

from __future__ import annotations

# canonical -> aliases
CANONICAL_ALIASES: dict[str, tuple[str, ...]] = {
    "Annual Leave": (
        "leave",
        "leaves",
        "vacation",
        "paid leave",
        "annual leave",
        "time off",
        "pto",
    ),
    "VPN": (
        "vpn",
        "virtual private network",
        "corporate vpn",
        "company vpn",
    ),
    "Multi-Factor Authentication": (
        "mfa",
        "2fa",
        "two factor",
        "multi factor authentication",
        "multi-factor authentication",
    ),
    "Remote Work": (
        "remote work",
        "work from home",
        "wfh",
        "hybrid work",
        "telework",
    ),
    "Incident Response": (
        "incident response",
        "security incident",
        "ir playbook",
        "breach response",
    ),
    "Performance Review": (
        "performance review",
        "performance management",
        "appraisal",
    ),
    "Budget": (
        "budget",
        "budgets",
        "budgeting",
        "department budget",
    ),
    "Expense Report": (
        "expense",
        "expenses",
        "expense report",
        "expense reports",
        "reimbursement",
    ),
    "Password Policy": (
        "password",
        "password policy",
        "passphrase policy",
        "credential policy",
    ),
}


def build_alias_lookup() -> dict[str, str]:
    """Return normalized alias -> canonical term."""
    lookup: dict[str, str] = {}
    for canonical, aliases in CANONICAL_ALIASES.items():
        lookup[canonical.lower()] = canonical
        for alias in aliases:
            lookup[alias.lower()] = canonical
    return lookup
