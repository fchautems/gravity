"""Small cached Numba kernel used only to validate the compiled runtime."""

from __future__ import annotations

import numpy as np
from numba import njit


@njit(cache=True)
def weighted_checksum(values: np.ndarray) -> float:
    """Return a deterministic checksum using an actual compiled loop."""

    total = 0.0
    for index in range(values.size):
        total += (index + 1) * values[index]
    return total
