"""Symmetric exact Newtonian reference solver."""

from __future__ import annotations

import math

import numpy as np
from numba import njit

from gravity.core.state import FloatArray
from gravity.physics.validation import validate_softening


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


def _validate_inputs(positions: FloatArray, masses: FloatArray) -> int:
    if not isinstance(positions, np.ndarray) or positions.dtype != np.float64:
        raise TypeError("positions must be a float64 NumPy array")
    if positions.ndim != 2 or positions.shape[1:] != (3,):
        raise ValueError("positions must have shape (N, 3)")
    if not positions.flags.c_contiguous:
        raise ValueError("positions must be C-contiguous")
    particle_count = int(positions.shape[0])
    if particle_count < 1:
        raise ValueError("at least one particle is required")
    if not np.all(np.isfinite(positions)):
        raise ValueError("positions must contain only finite values")

    if not isinstance(masses, np.ndarray) or masses.dtype != np.float64:
        raise TypeError("masses must be a float64 NumPy array")
    if masses.shape != (particle_count,):
        raise ValueError(f"masses must have shape ({particle_count},)")
    if not masses.flags.c_contiguous:
        raise ValueError("masses must be C-contiguous")
    if not np.all(np.isfinite(masses)) or np.any(masses <= 0.0):
        raise ValueError("masses must be finite and strictly positive")
    return particle_count


def _prepare_output(
    positions: FloatArray,
    masses: FloatArray,
    particle_count: int,
    output_buffer: FloatArray | None,
) -> FloatArray:
    if output_buffer is None:
        return np.empty((particle_count, 3), dtype=np.float64)
    if not isinstance(output_buffer, np.ndarray) or output_buffer.dtype != np.float64:
        raise TypeError("output_buffer must be a float64 NumPy array")
    if output_buffer.shape != (particle_count, 3):
        raise ValueError(f"output_buffer must have shape ({particle_count}, 3)")
    if not output_buffer.flags.c_contiguous or not output_buffer.flags.writeable:
        raise ValueError("output_buffer must be C-contiguous and writeable")
    if np.shares_memory(output_buffer, positions) or np.shares_memory(output_buffer, masses):
        raise ValueError("output_buffer cannot overlap solver inputs")
    return output_buffer


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
        particle_count = _validate_inputs(positions, masses)
        output = _prepare_output(positions, masses, particle_count, output_buffer)
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
