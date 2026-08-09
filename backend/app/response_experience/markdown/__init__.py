"""Phase 5B — Enterprise Markdown Renderer."""

from __future__ import annotations

from typing import Any

__all__ = [
    "RenderResult",
    "content_preserved",
    "render_enterprise_markdown",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from app.response_experience.markdown import renderer as _renderer

        return getattr(_renderer, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
