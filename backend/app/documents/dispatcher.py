"""Minimal in-process lifecycle event dispatcher."""

from __future__ import annotations

from collections.abc import Callable

from app.documents.events import DocumentLifecycleEvent

LifecycleEventHandler = Callable[[DocumentLifecycleEvent], None]


class LifecycleEventCollector:
    """Collect and dispatch document lifecycle events within the process.

    This is intentionally lightweight — no message bus, no persistence.
    Handlers register via ``subscribe()``; ``DocumentService`` publishes
    through ``publish()`` after successful lifecycle operations.
    """

    def __init__(self) -> None:
        self._handlers: list[LifecycleEventHandler] = []
        self.history: list[DocumentLifecycleEvent] = []

    def subscribe(self, handler: LifecycleEventHandler) -> None:
        """Register a handler invoked on every published event."""
        self._handlers.append(handler)

    def publish(self, event: DocumentLifecycleEvent) -> None:
        """Record and dispatch a lifecycle event to all subscribers."""
        self.history.append(event)
        for handler in self._handlers:
            handler(event)

    def clear(self) -> None:
        """Reset handler history (intended for tests)."""
        self.history.clear()


_default_collector = LifecycleEventCollector()


def get_lifecycle_event_collector() -> LifecycleEventCollector:
    """Return the shared in-process lifecycle event collector."""
    return _default_collector
