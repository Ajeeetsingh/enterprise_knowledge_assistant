"""Converter registry — register new pipelines without changing callers."""

from __future__ import annotations

from typing import TypeVar

from toolkit.converters.base import BaseConverter

T = TypeVar("T", bound=BaseConverter)


class ConverterRegistry:
    def __init__(self) -> None:
        self._converters: dict[str, BaseConverter] = {}

    def register(self, converter: T) -> T:
        key = converter.name
        if key in self._converters:
            raise ValueError(f"Converter already registered: {key}")
        self._converters[key] = converter
        return converter

    def get(self, name: str) -> BaseConverter:
        try:
            return self._converters[name]
        except KeyError as exc:
            known = ", ".join(sorted(self._converters)) or "(none)"
            raise KeyError(f"Unknown converter '{name}'. Registered: {known}") from exc

    def names(self) -> list[str]:
        return sorted(self._converters)

    def all(self) -> list[BaseConverter]:
        return [self._converters[k] for k in self.names()]


_DEFAULT: ConverterRegistry | None = None


def get_default_registry() -> ConverterRegistry:
    """Lazy singleton with built-in converters registered."""
    global _DEFAULT
    if _DEFAULT is None:
        from toolkit.converters.markdown_to_pdf import MarkdownToPdfConverter

        registry = ConverterRegistry()
        registry.register(MarkdownToPdfConverter())
        # Future:
        # registry.register(MarkdownToDocxConverter())
        # registry.register(ScannedPdfGenerator())
        # registry.register(OcrDatasetGenerator())
        _DEFAULT = registry
    return _DEFAULT
