from __future__ import annotations

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from gravity.diagnostics import compare_accelerations
from gravity.physics import BarnesHutSolver, ExactGravitySolver
from gravity.scenarios import GalaxyConfig, generate_spiral_galaxy


def test_one_and_two_particle_results_match_the_exact_solver() -> None:
    solver = BarnesHutSolver()
    single_positions = np.array([[4.0, -2.0, 1.0]], dtype=np.float64)
    single_masses = np.array([3.0], dtype=np.float64)
    assert np.array_equal(
        solver.compute(single_positions, single_masses, 0.1),
        np.zeros((1, 3)),
    )

    positions = np.array([[-1.0, 0.2, 0.4], [2.0, -0.5, 0.8]], dtype=np.float64)
    masses = np.array([0.7, 2.3], dtype=np.float64)
    approximate = solver.compute(positions, masses, 0.04)
    exact = ExactGravitySolver().compute(positions, masses, 0.04)
    np.testing.assert_array_equal(approximate, exact)


def test_default_theta_meets_the_seeded_galaxy_error_budget() -> None:
    galaxy = generate_spiral_galaxy(GalaxyConfig(particle_count=512, seed=1_234))
    exact = ExactGravitySolver().compute(
        galaxy.state.positions,
        galaxy.state.masses,
        galaxy.config.softening,
    )
    approximate = BarnesHutSolver().compute(
        galaxy.state.positions,
        galaxy.state.masses,
        galaxy.config.softening,
    )
    report = compare_accelerations(exact, approximate)
    assert report.meets_v1_budget()
    assert report.median_relative_error < 0.015
    assert report.percentile_95_relative_error < 0.04


def test_default_theta_meets_budget_on_a_non_galactic_clustered_cloud() -> None:
    rng = np.random.default_rng(86_753_090)
    cluster_centers = np.array(
        [[-2.0, 0.0, 0.5], [2.0, 0.3, -0.4], [0.1, 2.5, 1.0]],
        dtype=np.float64,
    )
    cluster = rng.integers(0, cluster_centers.shape[0], size=384)
    positions = np.ascontiguousarray(
        cluster_centers[cluster] + rng.normal(0.0, 0.35, size=(384, 3)),
        dtype=np.float64,
    )
    masses = np.ascontiguousarray(rng.lognormal(-0.2, 0.7, size=384), dtype=np.float64)
    exact = ExactGravitySolver().compute(positions, masses, 0.05)
    approximate = BarnesHutSolver().compute(positions, masses, 0.05)
    assert compare_accelerations(exact, approximate).meets_v1_budget()


def test_smaller_theta_is_more_accurate_than_a_large_opening_angle() -> None:
    galaxy = generate_spiral_galaxy(GalaxyConfig(particle_count=400, seed=99))
    state = galaxy.state
    exact = ExactGravitySolver().compute(state.positions, state.masses, galaxy.config.softening)
    strict = compare_accelerations(
        exact,
        BarnesHutSolver(theta=0.3).compute(
            state.positions,
            state.masses,
            galaxy.config.softening,
        ),
    )
    loose = compare_accelerations(
        exact,
        BarnesHutSolver(theta=1.2).compute(
            state.positions,
            state.masses,
            galaxy.config.softening,
        ),
    )
    assert strict.median_relative_error < loose.median_relative_error
    assert strict.percentile_95_relative_error < loose.percentile_95_relative_error


def test_coincident_particles_are_finite_and_do_not_attract_each_other() -> None:
    positions = np.zeros((70, 3), dtype=np.float64)
    masses = np.linspace(0.1, 2.0, positions.shape[0], dtype=np.float64)
    solver = BarnesHutSolver(leaf_capacity=1, depth_limit=8)
    result = solver.compute(positions, masses, 0.1)
    assert np.array_equal(result, np.zeros_like(result))
    assert solver.last_stats is not None
    assert solver.last_stats.maximum_depth == 8
    assert solver.last_stats.direct_particle_interactions == 70 * 69


def test_output_buffer_and_last_run_instrumentation_are_reused_and_complete() -> None:
    rng = np.random.default_rng(42)
    positions = np.ascontiguousarray(rng.normal(size=(120, 3)), dtype=np.float64)
    masses = np.ascontiguousarray(rng.uniform(0.2, 1.0, size=120), dtype=np.float64)
    output = np.full_like(positions, np.nan)
    solver = BarnesHutSolver()
    result = solver.compute(positions, masses, 0.08, output)
    assert result is output
    assert np.all(np.isfinite(result))
    stats = solver.last_stats
    assert stats is not None
    assert stats.particle_count == positions.shape[0]
    assert stats.node_count >= stats.leaf_count > 0
    assert 0 <= stats.maximum_depth <= solver.depth_limit
    assert stats.tree_build_seconds >= 0.0
    assert stats.force_seconds >= 0.0
    assert stats.total_seconds == stats.tree_build_seconds + stats.force_seconds
    assert stats.accepted_node_interactions > 0
    assert stats.direct_particle_interactions > 0


def test_parallel_and_sequential_traversals_are_bitwise_identical() -> None:
    galaxy = generate_spiral_galaxy(GalaxyConfig(particle_count=2_100, seed=2718))
    state = galaxy.state
    sequential = BarnesHutSolver(parallel_threshold=3_000).compute(
        state.positions,
        state.masses,
        galaxy.config.softening,
    )
    parallel = BarnesHutSolver(parallel_threshold=2_000).compute(
        state.positions,
        state.masses,
        galaxy.config.softening,
    )
    np.testing.assert_array_equal(parallel, sequential)


@pytest.mark.parametrize(
    ("keyword", "value", "error"),
    [
        ("theta", 0.29, ValueError),
        ("theta", 1.21, ValueError),
        ("theta", float("nan"), ValueError),
        ("theta", object(), TypeError),
        ("leaf_capacity", 0, ValueError),
        ("leaf_capacity", True, TypeError),
        ("depth_limit", 0, ValueError),
        ("parallel_threshold", 0, ValueError),
    ],
)
def test_solver_configuration_is_validated(
    keyword: str,
    value: object,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        BarnesHutSolver(**{keyword: value})  # type: ignore[arg-type]


def test_validated_solver_configuration_is_immutable() -> None:
    solver = BarnesHutSolver()
    with pytest.raises(FrozenInstanceError):
        solver.theta = 1.0  # type: ignore[misc]


def test_solver_uses_the_shared_input_and_output_safety_boundary() -> None:
    solver = BarnesHutSolver()
    positions = np.zeros((2, 3), dtype=np.float64)
    masses = np.ones(2, dtype=np.float64)
    with pytest.raises(TypeError):
        solver.compute(positions.astype(np.float32), masses, 0.1)
    with pytest.raises(ValueError, match="strictly positive"):
        solver.compute(positions, np.array([1.0, 0.0]), 0.1)
    with pytest.raises(ValueError, match="overlap"):
        solver.compute(positions, masses, 0.1, positions)
