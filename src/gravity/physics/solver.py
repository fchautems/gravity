"""Stable solver boundary shared by exact and future approximate backends."""

from __future__ import annotations

from typing import Protocol

from gravity.core.state import FloatArray


class AccelerationSolver(Protocol):
    """Compute accelerations for one complete particle state."""

    @property
    def name(self) -> str:
        """Stable backend identifier."""

    def compute(
        self,
        positions: FloatArray,
        masses: FloatArray,
        softening: float,
        output_buffer: FloatArray | None = None,
    ) -> FloatArray:
        """Fill and return ``output_buffer``, or allocate one when omitted."""
