from __future__ import annotations

import math

import numpy as np
import pytest

from gravity.core.state import ParticleState
from gravity.physics.invariants import (
    _softened_potential_energy_kernel,
    angular_momentum,
    center_of_mass,
    kinetic_energy,
    softened_potential_energy,
    total_energy,
    total_mass,
    total_momentum,
)


def _known_state() -> ParticleState:
    return ParticleState.from_arrays(
        positions=[[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        velocities=[[0.0, 1.0, 0.0], [0.0, -2.0, 0.0]],
        masses=[2.0, 1.0],
    )


def test_known_mass_momentum_energy_and_angular_momentum() -> None:
    state = _known_state()
    softening = 0.25
    assert total_mass(state) == 3.0
    np.testing.assert_allclose(center_of_mass(state), [-1.0 / 3.0, 0.0, 0.0])
    np.testing.assert_array_equal(total_momentum(state), np.zeros(3))
    np.testing.assert_allclose(angular_momentum(state), [0.0, 0.0, -4.0])
    assert kinetic_energy(state) == 3.0
    expected_potential = -2.0 / math.sqrt(4.0 + softening * softening)
    assert softened_potential_energy(state, softening) == pytest.approx(expected_potential)
    assert total_energy(state, softening) == pytest.approx(3.0 + expected_potential)


def test_compiled_and_python_potential_energy_kernels_agree() -> None:
    state = _known_state()
    compiled = softened_potential_energy(state, 0.1)
    interpreted = _softened_potential_energy_kernel.py_func(
        state.positions,
        state.masses,
        0.1**2,
    )
    assert compiled == interpreted


def test_potential_energy_rejects_invalid_softening() -> None:
    with pytest.raises(ValueError):
        softened_potential_energy(_known_state(), -1.0)
