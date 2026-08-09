"""Priority tiers for Phase 4C answer composition."""

from __future__ import annotations

from enum import Enum


class EvidencePriority(str, Enum):
    """How strongly the LLM should rely on an evidence group."""

    PRIMARY = "primary"
    SUPPORTING = "supporting"
    OPTIONAL = "optional"
