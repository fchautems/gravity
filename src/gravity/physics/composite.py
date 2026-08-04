"""Composition of particle self-gravity and independent analytic fields."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from gravity.core.state import FloatArray
from gravity.physics.solver import AccelerationSolver


class AdditiveAccelerationField(Protocol):
    """Analytic field that can add acceleration to a complete output array."""

    @property
    def name(self) -> str:
        """Stable analytic-field identifier."""

    def add_acceleration(self, positions: FloatArray, output_buffer: FloatArray) -> None:
        """Add acceleration for all positions to ``output_buffer`` in place."""


@dataclass(frozen=True, slots=True)
class CompositeGravitySolver:
    """Apply self-gravity first, then explicitly configured external fields."""

    self_gravity: AccelerationSolver
    external_fields: tuple[AdditiveAccelerationField, ...] = ()
    name: str = "composite"

    def __post_init__(self) -> None:
        if not callable(getattr(self.self_gravity, "compute", None)):
            raise TypeError("self_gravity must implement compute")
        for field in self.external_fields:
            if not callable(getattr(field, "add_acceleration", None)):
                raise TypeError("every external field must implement add_acceleration")

    def compute(
        self,
        positions: FloatArray,
        masses: FloatArray,
        softening: float,
        output_buffer: FloatArray | None = None,
    ) -> FloatArray:
        output = self.self_gravity.compute(positions, masses, softening, output_buffer)
        for field in self.external_fields:
            field.add_acceleration(positions, output)
        if not np.all(np.isfinite(output)):
            raise FloatingPointError("composite gravity produced a non-finite acceleration")
        return output
