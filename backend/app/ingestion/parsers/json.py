"""JSON document parser."""

from __future__ import annotations

import json

from app.ingestion.parsers.base import DocumentParser


class JsonParser(DocumentParser):
    """Parse JSON files into readable text.

    Handles the security log / employee record shapes used in the prototype
    as well as arbitrary dicts and lists.
    """

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".json"})

    def parse(self, content: bytes, filename: str) -> str:
        try:
            data = json.loads(content.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return content.decode("utf-8", errors="replace")

        return self._flatten(data)

    def _flatten(self, data: object, depth: int = 0) -> str:
        if isinstance(data, dict):
            parts: list[str] = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    parts.append(f"{key}: {self._flatten(value, depth + 1)}")
                else:
                    parts.append(f"{key}: {value}")
            return "\n".join(parts)
        if isinstance(data, list):
            return "\n".join(self._flatten(item, depth + 1) for item in data)
        return str(data)
