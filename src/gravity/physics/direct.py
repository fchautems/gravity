"""Symmetric exact Newtonian reference solver."""

from __future__ import annotations

import math

import numpy as np
from numba import njit

from gravity.core.state import FloatArray
from gravity.physics.validation import (
    prepare_acceleration_output,
    validate_softening,
    validate_solver_inputs,
)


@njit(cache=True, nogil=True)
def _direct_acceleration_kernel(
    positions: FloatArray,
    masses: FloatArray,
    softening_squared: float,
    output: FloatArray,
) -> None:
    particle_count = positions.shape[0]
    for index in range(particle_count):
        output[index, 0] = 0.0
        output[index, 1] = 0.0
        output[index, 2] = 0.0

    for first in range(particle_count - 1):
        for second in range(first + 1, particle_count):
            dx = positions[second, 0] - positions[first, 0]
            dy = positions[second, 1] - positions[first, 1]
            dz = positions[second, 2] - positions[first, 2]
            softened_squared_distance = dx * dx + dy * dy + dz * dz + softening_squared
            inverse_distance_cubed = 1.0 / (
                softened_squared_distance * math.sqrt(softened_squared_distance)
            )

            first_scale = masses[second] * inverse_distance_cubed
            second_scale = masses[first] * inverse_distance_cubed
            output[first, 0] += dx * first_scale
            output[first, 1] += dy * first_scale
            output[first, 2] += dz * first_scale
            output[second, 0] -= dx * second_scale
            output[second, 1] -= dy * second_scale
            output[second, 2] -= dz * second_scale


class ExactGravitySolver:
    """Evaluate each unordered pair once in ``O(N^2)`` time and ``O(N)`` memory."""

    name = "exact"

    def compute(
        self,
        positions: FloatArray,
        masses: FloatArray,
        softening: float,
        output_buffer: FloatArray | None = None,
    ) -> FloatArray:
        particle_count = validate_solver_inputs(positions, masses)
        output = prepare_acceleration_output(
            positions,
            masses,
            particle_count,
            output_buffer,
        )
        safe_softening = validate_softening(softening)
        _direct_acceleration_kernel(
            positions,
            masses,
            safe_softening * safe_softening,
            output,
        )
        if not np.all(np.isfinite(output)):
            raise FloatingPointError("exact gravity produced a non-finite acceleration")
        return output
