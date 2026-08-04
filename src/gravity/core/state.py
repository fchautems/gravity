"""Validated structure-of-arrays state owned by the physics engine."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

type FloatArray = npt.NDArray[np.float64]
type IdArray = npt.NDArray[np.uint64]


def _require_array(value: object, name: str) -> np.ndarray:
    if not isinstance(value, np.ndarray):
        raise TypeError(f"{name} must be a NumPy array")
    return value


def _validate_float_matrix(value: object, name: str, particle_count: int) -> FloatArray:
    array = _require_array(value, name)
    if array.dtype != np.float64:
        raise TypeError(f"{name} must use float64")
    if array.shape != (particle_count, 3):
        raise ValueError(f"{name} must have shape ({particle_count}, 3)")
    if not array.flags.c_contiguous:
        raise ValueError(f"{name} must be C-contiguous")
    if not array.flags.writeable:
        raise ValueError(f"{name} must be writeable")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


@dataclass(slots=True)
class ParticleState:
    """Mutable physics state with no Python object per particle.

    Callers that modify ``positions`` or ``masses`` outside an integrator must
    call :meth:`invalidate_accelerations` before the next step.
    """

    positions: FloatArray = field(repr=False)
    velocities: FloatArray = field(repr=False)
    accelerations: FloatArray = field(repr=False)
    masses: FloatArray = field(repr=False)
    ids: IdArray = field(repr=False)
    simulation_time: float = 0.0
    step_count: int = 0
    _accelerations_valid: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        self.validate()

    @classmethod
    def from_arrays(
        cls,
        positions: npt.ArrayLike,
        velocities: npt.ArrayLike,
        masses: npt.ArrayLike,
        *,
        ids: npt.ArrayLike | None = None,
    ) -> ParticleState:
        """Copy compatible inputs into the strict internal array contract."""

        position_array = np.array(positions, dtype=np.float64, order="C", copy=True)
        velocity_array = np.array(velocities, dtype=np.float64, order="C", copy=True)
        mass_array = np.array(masses, dtype=np.float64, order="C", copy=True)
        if position_array.ndim != 2 or position_array.shape[1:] != (3,):
            raise ValueError("positions must have shape (N, 3)")
        particle_count = int(position_array.shape[0])
        if ids is None:
            id_array = np.arange(particle_count, dtype=np.uint64)
        else:
            raw_ids = np.asarray(ids)
            if raw_ids.ndim != 1 or raw_ids.shape != (particle_count,):
                raise ValueError(f"ids must have shape ({particle_count},)")
            if not np.issubdtype(raw_ids.dtype, np.integer):
                raise TypeError("ids must contain integers")
            if np.any(raw_ids < 0):
                raise ValueError("ids cannot be negative")
            id_array = np.array(raw_ids, dtype=np.uint64, order="C", copy=True)
        accelerations = np.zeros((particle_count, 3), dtype=np.float64)
        return cls(
            position_array,
            velocity_array,
            accelerations,
            mass_array,
            id_array,
        )

    @property
    def particle_count(self) -> int:
        return int(self.positions.shape[0])

    @property
    def accelerations_valid(self) -> bool:
        return self._accelerations_valid

    def mark_accelerations_valid(self) -> None:
        self._accelerations_valid = True

    def invalidate_accelerations(self) -> None:
        self._accelerations_valid = False

    def validate(self) -> None:
        """Recheck the complete state boundary and raise on corruption."""

        positions = _require_array(self.positions, "positions")
        if positions.ndim != 2 or positions.shape[1:] != (3,):
            raise ValueError("positions must have shape (N, 3)")
        particle_count = int(positions.shape[0])
        if particle_count < 1:
            raise ValueError("particle state cannot be empty")
        self.positions = _validate_float_matrix(positions, "positions", particle_count)
        self.velocities = _validate_float_matrix(
            self.velocities,
            "velocities",
            particle_count,
        )
        self.accelerations = _validate_float_matrix(
            self.accelerations,
            "accelerations",
            particle_count,
        )

        masses = _require_array(self.masses, "masses")
        if masses.dtype != np.float64:
            raise TypeError("masses must use float64")
        if masses.shape != (particle_count,):
            raise ValueError(f"masses must have shape ({particle_count},)")
        if not masses.flags.c_contiguous:
            raise ValueError("masses must be C-contiguous")
        if not np.all(np.isfinite(masses)):
            raise ValueError("masses must contain only finite values")
        if np.any(masses <= 0.0):
            raise ValueError("masses must be strictly positive")

        ids = _require_array(self.ids, "ids")
        if ids.dtype != np.uint64:
            raise TypeError("ids must use uint64")
        if ids.shape != (particle_count,):
            raise ValueError(f"ids must have shape ({particle_count},)")
        if not ids.flags.c_contiguous:
            raise ValueError("ids must be C-contiguous")
        if np.unique(ids).size != particle_count:
            raise ValueError("particle ids must be unique")

        if not math.isfinite(self.simulation_time) or self.simulation_time < 0.0:
            raise ValueError("simulation_time must be finite and non-negative")
        if isinstance(self.step_count, bool) or not isinstance(self.step_count, int):
            raise TypeError("step_count must be an integer")
        if self.step_count < 0:
            raise ValueError("step_count cannot be negative")

    def copy(self) -> ParticleState:
        """Return a deep, independently mutable copy of the state."""

        return ParticleState(
            positions=self.positions.copy(),
            velocities=self.velocities.copy(),
            accelerations=self.accelerations.copy(),
            masses=self.masses.copy(),
            ids=self.ids.copy(),
            simulation_time=self.simulation_time,
            step_count=self.step_count,
            _accelerations_valid=self._accelerations_valid,
        )
