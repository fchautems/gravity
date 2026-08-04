from __future__ import annotations

import numpy as np
import pytest

from gravity.core.state import ParticleState
from gravity.physics.direct import ExactGravitySolver
from gravity.physics.integrator import LeapfrogIntegrator
from gravity.physics.invariants import center_of_mass, total_energy, total_momentum
from tests.physics.conftest import CircularBinary


def test_free_particle_moves_linearly_without_self_force() -> None:
    state = ParticleState.from_arrays(
        positions=[[1.0, 2.0, 3.0]],
        velocities=[[0.5, -0.25, 2.0]],
        masses=[7.0],
    )
    integrator = LeapfrogIntegrator(ExactGravitySolver(), time_step=0.125, softening=0.1)
    integrator.step(state, steps=8)
    np.testing.assert_allclose(state.positions, [[1.5, 1.75, 5.0]], rtol=0.0, atol=1e-15)
    np.testing.assert_array_equal(state.velocities, [[0.5, -0.25, 2.0]])
    np.testing.assert_array_equal(state.accelerations, np.zeros((1, 3)))
    assert state.accelerations_valid
    assert state.simulation_time == 1.0
    assert state.step_count == 8


def test_integrator_reuses_current_acceleration_until_invalidated() -> None:
    class CountingSolver(ExactGravitySolver):
        def __init__(self) -> None:
            self.calls = 0

        def compute(self, *args: object, **kwargs: object) -> np.ndarray:
            self.calls += 1
            return super().compute(*args, **kwargs)  # type: ignore[arg-type]

    solver = CountingSolver()
    state = ParticleState.from_arrays([[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [1.0])
    integrator = LeapfrogIntegrator(solver, time_step=0.1, softening=0.1)
    integrator.step(state, steps=3)
    assert solver.calls == 4
    integrator.step(state, steps=2)
    assert solver.calls == 6
    state.invalidate_accelerations()
    integrator.step(state)
    assert solver.calls == 8


def test_circular_binary_meets_the_100_orbit_energy_and_com_budgets(
    circular_binary: CircularBinary,
) -> None:
    state = circular_binary.state
    initial_energy = total_energy(state, circular_binary.softening)
    initial_com = center_of_mass(state).copy()
    initial_momentum = total_momentum(state).copy()
    steps_per_orbit = 256
    time_step = circular_binary.period / steps_per_orbit
    integrator = LeapfrogIntegrator(
        ExactGravitySolver(),
        time_step=time_step,
        softening=circular_binary.softening,
    )
    integrator.step(state, steps=100 * steps_per_orbit)

    final_energy = total_energy(state, circular_binary.softening)
    relative_energy_drift = abs((final_energy - initial_energy) / initial_energy)
    com_drift = float(np.linalg.norm(center_of_mass(state) - initial_com))
    momentum_drift = float(np.linalg.norm(total_momentum(state) - initial_momentum))
    separation = float(np.linalg.norm(state.positions[1] - state.positions[0]))

    assert relative_energy_drift < 1e-3
    assert com_drift <= 1e-9
    assert momentum_drift <= 1e-12
    assert separation == pytest.approx(1.0, rel=2e-3)
    assert state.step_count == 25_600
    assert state.simulation_time == pytest.approx(100 * circular_binary.period)


@pytest.mark.parametrize("time_step", [0.0, -0.1, float("nan"), float("inf")])
def test_integrator_rejects_non_positive_or_non_finite_time_steps(time_step: float) -> None:
    with pytest.raises(ValueError):
        LeapfrogIntegrator(ExactGravitySolver(), time_step=time_step, softening=0.1)


@pytest.mark.parametrize("steps", [0, -1, 1.5, True])
def test_integrator_rejects_invalid_step_counts(steps: object) -> None:
    state = ParticleState.from_arrays([[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [1.0])
    integrator = LeapfrogIntegrator(ExactGravitySolver(), time_step=0.1, softening=0.1)
    with pytest.raises((TypeError, ValueError)):
        integrator.step(state, steps=steps)  # type: ignore[arg-type]
