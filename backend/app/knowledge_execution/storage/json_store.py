"""Persist CandidateEvidenceSet snapshots (Shadow Mode)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ExecutionResultJsonStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshot_path = self.root / "execution_results.json"
        self._results: list[dict[str, Any]] = []
        existing = self.load()
        if existing:
            self._results = list(existing.get("results") or [])

    def append(self, result: dict[str, Any], *, limit: int = 300) -> Path:
        self._results.append(result)
        self._results = self._results[-limit:]
        payload = {"results": self._results, "count": len(self._results)}
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.snapshot_path

    def load(self) -> dict[str, Any] | None:
        if not self.snapshot_path.exists():
            return None
        return json.loads(self.snapshot_path.read_text(encoding="utf-8"))
