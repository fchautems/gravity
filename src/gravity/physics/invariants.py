"""Physical invariants and diagnostics for exact-reference validation."""

from __future__ import annotations

import math
from typing import cast

import numpy as np
from numba import njit

from gravity.core.state import FloatArray, ParticleState
from gravity.physics.validation import validate_softening


@njit(cache=True, nogil=True)
def _softened_potential_energy_kernel(
    positions: np.ndarray,
    masses: np.ndarray,
    softening_squared: float,
) -> float:
    energy = 0.0
    particle_count = positions.shape[0]
    for first in range(particle_count - 1):
        for second in range(first + 1, particle_count):
            dx = positions[second, 0] - positions[first, 0]
            dy = positions[second, 1] - positions[first, 1]
            dz = positions[second, 2] - positions[first, 2]
            softened_squared_distance = dx * dx + dy * dy + dz * dz + softening_squared
            energy -= masses[first] * masses[second] / math.sqrt(softened_squared_distance)
    return energy


def total_mass(state: ParticleState) -> float:
    state.validate()
    return float(np.sum(state.masses, dtype=np.float64))


def center_of_mass(state: ParticleState) -> FloatArray:
    state.validate()
    result = np.sum(state.positions * state.masses[:, None], axis=0) / total_mass(state)
    return cast(FloatArray, result)


def total_momentum(state: ParticleState) -> FloatArray:
    state.validate()
    return cast(FloatArray, np.sum(state.velocities * state.masses[:, None], axis=0))


def angular_momentum(state: ParticleState) -> FloatArray:
    state.validate()
    momentum = state.velocities * state.masses[:, None]
    return cast(FloatArray, np.sum(np.cross(state.positions, momentum), axis=0))


def kinetic_energy(state: ParticleState) -> float:
    state.validate()
    speed_squared = np.einsum("ij,ij->i", state.velocities, state.velocities)
    return float(0.5 * np.dot(state.masses, speed_squared))


def softened_potential_energy(state: ParticleState, softening: float) -> float:
    state.validate()
    safe_softening = validate_softening(softening)
    result = float(
        _softened_potential_energy_kernel(
            state.positions,
            state.masses,
            safe_softening * safe_softening,
        )
    )
    if not math.isfinite(result):
        raise FloatingPointError("potential-energy calculation produced a non-finite value")
    return result


def total_energy(state: ParticleState, softening: float) -> float:
    return kinetic_energy(state) + softened_potential_energy(state, softening)
