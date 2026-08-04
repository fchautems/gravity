"""Validation shared by numerical components."""

from __future__ import annotations

import math

import numpy as np

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
