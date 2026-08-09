"""Persist shadow QueryExecutionPlan snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class QueryPlanJsonStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshot_path = self.root / "query_plans.json"
        self._plans: list[dict[str, Any]] = []
        existing = self.load()
        if existing:
            self._plans = list(existing.get("plans") or [])

    def append(self, plan: dict[str, Any], *, limit: int = 500) -> Path:
        self._plans.append(plan)
        self._plans = self._plans[-limit:]
        payload = {"plans": self._plans, "count": len(self._plans)}
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.snapshot_path

    def load(self) -> dict[str, Any] | None:
        if not self.snapshot_path.exists():
            return None
        return json.loads(self.snapshot_path.read_text(encoding="utf-8"))

    def clear(self) -> None:
        self._plans = []
        if self.snapshot_path.exists():
            self.snapshot_path.unlink()
