"""Fixed-step kick-drift-kick leapfrog integration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gravity.core.state import ParticleState
from gravity.physics.solver import AccelerationSolver
from gravity.physics.validation import validate_softening, validate_time_step


@dataclass(slots=True)
class LeapfrogIntegrator:
    """Advance one mutable state using a solver-independent symplectic scheme."""

    solver: AccelerationSolver
    time_step: float
    softening: float

    def __post_init__(self) -> None:
        if not callable(getattr(self.solver, "compute", None)):
            raise TypeError("solver must implement compute")
        self.time_step = validate_time_step(self.time_step)
        self.softening = validate_softening(self.softening)

    def initialize(self, state: ParticleState) -> None:
        """Compute acceleration for the state's current positions."""

        state.validate()
        self.solver.compute(
            state.positions,
            state.masses,
            self.softening,
            state.accelerations,
        )
        state.mark_accelerations_valid()

    def step(self, state: ParticleState, *, steps: int = 1) -> None:
        """Advance ``steps`` fixed increments in place."""

        if isinstance(steps, bool) or not isinstance(steps, (int, np.integer)):
            raise TypeError("steps must be an integer")
        step_total = int(steps)
        if step_total < 1:
            raise ValueError("steps must be strictly positive")
        state.validate()
        if not state.accelerations_valid:
            self.initialize(state)

        half_step = 0.5 * self.time_step
        for _ in range(step_total):
            state.velocities += half_step * state.accelerations
            state.positions += self.time_step * state.velocities
            state.invalidate_accelerations()
            self.solver.compute(
                state.positions,
                state.masses,
                self.softening,
                state.accelerations,
            )
            state.mark_accelerations_valid()
            state.velocities += half_step * state.accelerations
            state.simulation_time += self.time_step
            state.step_count += 1

        if not np.all(np.isfinite(state.velocities)):
            raise FloatingPointError("leapfrog produced a non-finite velocity")
