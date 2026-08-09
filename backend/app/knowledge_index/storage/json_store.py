"""JSON snapshot persistence for Hybrid Knowledge Indexes (Shadow Mode)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class KnowledgeIndexJsonStore:
    """Persist manager snapshots under the local indexes directory."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshot_path = self.root / "hybrid_knowledge_index.json"

    def save(self, payload: dict[str, Any]) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.snapshot_path

    def load(self) -> dict[str, Any] | None:
        if not self.snapshot_path.exists():
            return None
        return json.loads(self.snapshot_path.read_text(encoding="utf-8"))

    def size_bytes(self) -> int:
        if not self.snapshot_path.exists():
            return 0
        return self.snapshot_path.stat().st_size
