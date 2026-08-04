"""Immutable contracts exchanged between physics, UI, and rendering."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import numpy.typing as npt

type RenderPositionArray = npt.NDArray[np.float32]


class SolverMode(StrEnum):
    """User-selectable self-gravity backends."""

    BARNES_HUT = "barnes-hut"
    EXACT = "exact"

    @property
    def french_name(self) -> str:
        if self is SolverMode.BARNES_HUT:
            return "Barnes–Hut"
        return "Exact O(N²)"


@dataclass(frozen=True, slots=True)
class SimulationStatus:
    """Small presentation-only view of the latest complete physics state."""

    solver_mode: SolverMode
    particle_count: int
    simulation_time: float
    step_count: int
    generation: int
    paused: bool
    time_scale: float
    physics_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.solver_mode, SolverMode):
            raise TypeError("solver_mode must be a SolverMode")
        for name in ("particle_count", "step_count", "generation"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        if self.particle_count < 1:
            raise ValueError("particle_count must be positive")
        if self.step_count < 0 or self.generation < 0:
            raise ValueError("step_count and generation cannot be negative")
        for name in ("simulation_time", "physics_seconds"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")
        if not math.isfinite(self.time_scale) or self.time_scale <= 0.0:
            raise ValueError("time_scale must be finite and positive")

    @property
    def physics_ms(self) -> float:
        return self.physics_seconds * 1_000.0


@dataclass(frozen=True, slots=True)
class RenderSnapshot:
    """Read-only position copy published atomically by the physics worker."""

    positions: RenderPositionArray
    status: SimulationStatus

    def __post_init__(self) -> None:
        positions = self.positions
        if not isinstance(positions, np.ndarray):
            raise TypeError("positions must be a NumPy array")
        if positions.dtype != np.float32:
            raise TypeError("render positions must use float32")
        if positions.shape != (self.status.particle_count, 3):
            raise ValueError(f"render positions must have shape ({self.status.particle_count}, 3)")
        if not positions.flags.c_contiguous:
            raise ValueError("render positions must be C-contiguous")
        if not np.all(np.isfinite(positions)):
            raise ValueError("render positions must contain only finite values")
        positions.setflags(write=False)
