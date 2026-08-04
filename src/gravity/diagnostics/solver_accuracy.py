"""Deterministic acceleration-error reports for approximate gravity solvers."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from gravity.core.state import FloatArray

DEFAULT_RELATIVE_FLOOR_FRACTION = 1.0e-12
DEFAULT_MEDIAN_ERROR_LIMIT = 0.02
DEFAULT_PERCENTILE_95_ERROR_LIMIT = 0.05


def _acceleration_array(value: FloatArray, name: str) -> FloatArray:
    if not isinstance(value, np.ndarray) or value.dtype != np.float64:
        raise TypeError(f"{name} must be a float64 NumPy array")
    if value.ndim != 2 or value.shape[1:] != (3,):
        raise ValueError(f"{name} must have shape (N, 3)")
    if value.shape[0] < 1:
        raise ValueError(f"{name} cannot be empty")
    if not np.all(np.isfinite(value)):
        raise ValueError(f"{name} must contain only finite values")
    return value


@dataclass(frozen=True, slots=True)
class AccelerationErrorReport:
    """Norm-based approximation error with near-zero references separated."""

    sample_count: int
    relative_sample_count: int
    near_zero_sample_count: int
    reference_floor: float
    median_relative_error: float
    percentile_95_relative_error: float
    maximum_relative_error: float
    root_mean_square_absolute_error: float
    maximum_near_zero_absolute_error: float

    def meets_v1_budget(
        self,
        *,
        median_limit: float = DEFAULT_MEDIAN_ERROR_LIMIT,
        percentile_95_limit: float = DEFAULT_PERCENTILE_95_ERROR_LIMIT,
    ) -> bool:
        """Return whether the report satisfies the documented step-6 gate."""

        return (
            self.relative_sample_count > 0
            and self.median_relative_error <= median_limit
            and self.percentile_95_relative_error <= percentile_95_limit
        )


def compare_accelerations(
    reference: FloatArray,
    approximate: FloatArray,
    *,
    relative_floor: float | None = None,
) -> AccelerationErrorReport:
    """Compare vectors while excluding numerically near-zero references from ratios."""

    safe_reference = _acceleration_array(reference, "reference")
    safe_approximate = _acceleration_array(approximate, "approximate")
    if safe_approximate.shape != safe_reference.shape:
        raise ValueError("reference and approximate accelerations must have the same shape")

    reference_norm = np.linalg.norm(safe_reference, axis=1)
    absolute_error = np.linalg.norm(safe_approximate - safe_reference, axis=1)
    if relative_floor is None:
        scale = float(np.max(reference_norm))
        floor = max(np.finfo(np.float64).tiny, scale * DEFAULT_RELATIVE_FLOOR_FRACTION)
    else:
        try:
            floor = float(relative_floor)
        except (TypeError, ValueError) as error:
            raise TypeError("relative_floor must be a real number") from error
        if not math.isfinite(floor) or floor < 0.0:
            raise ValueError("relative_floor must be finite and non-negative")

    relative_mask = reference_norm > floor
    near_zero_mask = ~relative_mask
    relative_error = absolute_error[relative_mask] / reference_norm[relative_mask]
    if relative_error.size:
        median_relative = float(np.median(relative_error))
        percentile_95_relative = float(np.quantile(relative_error, 0.95))
        maximum_relative = float(np.max(relative_error))
    else:
        median_relative = 0.0
        percentile_95_relative = 0.0
        maximum_relative = 0.0
    maximum_near_zero = (
        float(np.max(absolute_error[near_zero_mask])) if np.any(near_zero_mask) else 0.0
    )
    return AccelerationErrorReport(
        sample_count=int(reference_norm.size),
        relative_sample_count=int(np.count_nonzero(relative_mask)),
        near_zero_sample_count=int(np.count_nonzero(near_zero_mask)),
        reference_floor=floor,
        median_relative_error=median_relative,
        percentile_95_relative_error=percentile_95_relative,
        maximum_relative_error=maximum_relative,
        root_mean_square_absolute_error=float(np.sqrt(np.mean(absolute_error**2))),
        maximum_near_zero_absolute_error=maximum_near_zero,
    )
