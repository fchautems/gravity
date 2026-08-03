"""Artificial step-3 animation clock, replaceable by physics snapshots later."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AnimationClock:
    elapsed: float = 0.0
    paused: bool = False
    speed: float = 1.0

    def advance(self, wall_seconds: float) -> None:
        if wall_seconds < 0.0:
            raise ValueError("wall_seconds cannot be negative")
        if not self.paused:
            self.elapsed += min(wall_seconds, 0.25) * self.speed

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def restart(self) -> None:
        self.elapsed = 0.0
