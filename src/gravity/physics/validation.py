"""Validation shared by numerical components."""

from __future__ import annotations

import math

import numpy as np

from gravity.core.state import FloatArray

MAX_SAFE_SOFTENING = math.sqrt(float(np.finfo(np.float64).max))
MIN_SAFE_SOFTENING = math.sqrt(float(np.finfo(np.float64).tiny))


def validate_softening(value: float) -> float:
    """Return a safe positive Plummer softening length."""

    try:
        softening = float(value)
    except (TypeError, ValueError) as error:
        raise TypeError("softening must be a real number") from error
    if not math.isfinite(softening):
        raise ValueError("softening must be finite")
    if softening < MIN_SAFE_SOFTENING or softening > MAX_SAFE_SOFTENING:
        raise ValueError("softening is outside the safe float64 range")
    return softening


def validate_time_step(value: float) -> float:
    """Return a finite, strictly positive fixed simulation step."""

    try:
        time_step = float(value)
    except (TypeError, ValueError) as error:
        raise TypeError("time_step must be a real number") from error
    if not math.isfinite(time_step) or time_step <= 0.0:
        raise ValueError("time_step must be finite and strictly positive")
    return time_step


def validate_solver_inputs(positions: FloatArray, masses: FloatArray) -> int:
    """Validate the shared, allocation-free acceleration-solver boundary."""

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


def prepare_acceleration_output(
    positions: FloatArray,
    masses: FloatArray,
    particle_count: int,
    output_buffer: FloatArray | None,
) -> FloatArray:
    """Return a safe solver output buffer with the common state shape."""

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
