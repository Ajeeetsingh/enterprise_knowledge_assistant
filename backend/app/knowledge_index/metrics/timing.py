"""Lightweight timing helpers for index metrics."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class LookupTimer:
    samples: deque[float] = field(default_factory=lambda: deque(maxlen=200))

    def record(self, elapsed_ms: float) -> None:
        self.samples.append(float(elapsed_ms))

    @property
    def average_ms(self) -> float:
        if not self.samples:
            return 0.0
        return sum(self.samples) / len(self.samples)


class Stopwatch:
    def __init__(self) -> None:
        self._started = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._started) * 1000.0
