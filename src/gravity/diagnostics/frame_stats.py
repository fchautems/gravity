"""Small rolling frame metrics for the in-app performance overlay."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from statistics import median


@dataclass(slots=True)
class FrameStats:
    sample_count: int = 120
    _frame_seconds: deque[float] = field(init=False)
    _draw_seconds: deque[float] = field(init=False)

    def __post_init__(self) -> None:
        if self.sample_count < 1:
            raise ValueError("sample_count must be positive")
        self._frame_seconds = deque(maxlen=self.sample_count)
        self._draw_seconds = deque(maxlen=self.sample_count)

    def record(self, frame_seconds: float, draw_seconds: float) -> None:
        if frame_seconds > 0.0:
            self._frame_seconds.append(frame_seconds)
        if draw_seconds >= 0.0:
            self._draw_seconds.append(draw_seconds)

    @property
    def fps(self) -> float:
        if not self._frame_seconds:
            return 0.0
        return 1.0 / median(self._frame_seconds)

    @property
    def frame_ms(self) -> float:
        if not self._frame_seconds:
            return 0.0
        return median(self._frame_seconds) * 1_000.0

    @property
    def draw_ms(self) -> float:
        if not self._draw_seconds:
            return 0.0
        return median(self._draw_seconds) * 1_000.0
