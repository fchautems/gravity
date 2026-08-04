from __future__ import annotations

import numpy as np
import pytest

from gravity.physics.direct import ExactGravitySolver, _direct_acceleration_kernel


def test_two_body_acceleration_matches_the_softened_analytic_result() -> None:
    positions = np.array([[-0.5, 0.0, 0.0], [0.5, 0.0, 0.0]], dtype=np.float64)
    masses = np.array([2.0, 3.0], dtype=np.float64)
    softening = 0.2
    acceleration = ExactGravitySolver().compute(positions, masses, softening)
    inverse_distance_cubed = (1.0 + softening * softening) ** -1.5
    expected = np.array(
        [
            [3.0 * inverse_distance_cubed, 0.0, 0.0],
            [-2.0 * inverse_distance_cubed, 0.0, 0.0],
        ],
        dtype=np.float64,
    )
    np.testing.assert_allclose(acceleration, expected, rtol=2e-15, atol=0.0)


def test_pair_forces_are_antisymmetric_for_unequal_seeded_masses() -> None:
    rng = np.random.default_rng(20260804)
    positions = np.ascontiguousarray(rng.normal(size=(32, 3)), dtype=np.float64)
    masses = np.ascontiguousarray(rng.uniform(0.1, 2.0, size=32), dtype=np.float64)
    acceleration = ExactGravitySolver().compute(positions, masses, 0.05)
    particle_forces = acceleration * masses[:, None]
    net_force = np.sum(particle_forces, axis=0)
    force_scale = float(np.max(np.sum(np.abs(particle_forces), axis=0)))
    roundoff_budget = 4.0 * np.finfo(np.float64).eps * force_scale
    np.testing.assert_allclose(net_force, np.zeros(3), rtol=0.0, atol=roundoff_budget)


def test_seeded_system_matches_an_independent_vectorized_oracle() -> None:
    rng = np.random.default_rng(4815162342)
    positions = np.ascontiguousarray(rng.normal(size=(9, 3)), dtype=np.float64)
    masses = np.ascontiguousarray(rng.uniform(0.2, 3.0, size=9), dtype=np.float64)
    softening = 0.07
    displacement = positions[None, :, :] - positions[:, None, :]
    softened_squared_distance = np.sum(displacement * displacement, axis=2) + softening**2
    weighted_inverse_cube = masses[None, :] / softened_squared_distance**1.5
    expected = np.sum(displacement * weighted_inverse_cube[:, :, None], axis=1)

    actual = ExactGravitySolver().compute(positions, masses, softening)
    np.testing.assert_allclose(actual, expected, rtol=3e-15, atol=3e-15)


def test_coincident_particles_remain_finite_and_exert_no_pair_force() -> None:
    positions = np.zeros((3, 3), dtype=np.float64)
    masses = np.array([1.0, 2.0, 4.0], dtype=np.float64)
    acceleration = ExactGravitySolver().compute(positions, masses, 0.1)
    assert np.array_equal(acceleration, np.zeros((3, 3)))
    assert np.all(np.isfinite(acceleration))


def test_single_particle_has_zero_self_acceleration() -> None:
    output = np.full((1, 3), 9.0, dtype=np.float64)
    result = ExactGravitySolver().compute(
        np.array([[3.0, -2.0, 8.0]], dtype=np.float64),
        np.array([5.0], dtype=np.float64),
        0.1,
        output,
    )
    assert result is output
    assert np.array_equal(result, np.zeros((1, 3)))


def test_compiled_and_python_reference_kernels_agree() -> None:
    positions = np.array(
        [[-1.0, 0.5, 0.2], [0.1, -0.4, 0.7], [1.4, 0.2, -0.9]],
        dtype=np.float64,
    )
    masses = np.array([0.5, 1.5, 2.0], dtype=np.float64)
    compiled = ExactGravitySolver().compute(positions, masses, 0.03)
    interpreted = np.empty_like(compiled)
    _direct_acceleration_kernel.py_func(positions, masses, 0.03**2, interpreted)
    np.testing.assert_array_equal(compiled, interpreted)


@pytest.mark.parametrize(
    ("positions", "masses", "softening", "error"),
    [
        (np.zeros((0, 3), dtype=np.float64), np.zeros(0), 0.1, ValueError),
        (np.zeros((2, 2), dtype=np.float64), np.ones(2), 0.1, ValueError),
        (np.zeros((2, 3), dtype=np.float32), np.ones(2), 0.1, TypeError),
        (np.full((2, 3), np.nan), np.ones(2), 0.1, ValueError),
        (np.zeros((2, 3)), np.ones(3), 0.1, ValueError),
        (np.zeros((2, 3)), np.array([1.0, 0.0]), 0.1, ValueError),
        (np.zeros((2, 3)), np.ones(2), 0.0, ValueError),
        (np.zeros((2, 3)), np.ones(2), float("inf"), ValueError),
    ],
)
def test_invalid_solver_boundaries_are_rejected(
    positions: np.ndarray,
    masses: np.ndarray,
    softening: float,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        ExactGravitySolver().compute(positions, masses, softening)


def test_output_buffer_must_be_safe_and_match_the_state() -> None:
    positions = np.zeros((2, 3), dtype=np.float64)
    masses = np.ones(2, dtype=np.float64)
    solver = ExactGravitySolver()
    with pytest.raises(TypeError):
        solver.compute(positions, masses, 0.1, np.zeros((2, 3), dtype=np.float32))
    with pytest.raises(ValueError, match="shape"):
        solver.compute(positions, masses, 0.1, np.zeros((3, 3), dtype=np.float64))
    with pytest.raises(ValueError, match="overlap"):
        solver.compute(positions, masses, 0.1, positions)
