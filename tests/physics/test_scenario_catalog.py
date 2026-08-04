from __future__ import annotations

import numpy as np
import pytest

from gravity.core.experiment import ExperimentConfig, ScenarioKind
from gravity.physics import center_of_mass, kinetic_energy, total_momentum
from gravity.scenarios import generate_experiment


@pytest.mark.parametrize("scenario", list(ScenarioKind))
def test_every_catalogue_scenario_is_reproducible_finite_and_centered(
    scenario: ScenarioKind,
) -> None:
    config = ExperimentConfig(scenario=scenario, particle_count=400, seed=123)
    first = generate_experiment(config)
    second = generate_experiment(config)
    assert first.name == scenario.french_name
    assert first.experiment == config
    assert first.state.particle_count == 400
    assert np.array_equal(first.state.positions, second.state.positions)
    assert np.array_equal(first.state.velocities, second.state.velocities)
    assert np.array_equal(first.state.masses, second.state.masses)
    assert np.array_equal(first.components, second.components)
    assert not first.components.flags.writeable
    assert np.linalg.norm(center_of_mass(first.state)) < 1e-14
    assert np.linalg.norm(total_momentum(first.state)) < 1e-14
    first.state.validate()


@pytest.mark.parametrize("scenario", list(ScenarioKind))
def test_different_seed_changes_each_catalogue_scenario(scenario: ScenarioKind) -> None:
    first = generate_experiment(ExperimentConfig(scenario, 400, 1))
    second = generate_experiment(ExperimentConfig(scenario, 400, 2))
    assert not np.array_equal(first.state.positions, second.state.positions)
    assert not np.array_equal(first.state.velocities, second.state.velocities)


def test_disk_ring_sphere_and_collision_have_distinct_spatial_signatures() -> None:
    disk = generate_experiment(ExperimentConfig(ScenarioKind.UNIFORM_DISK, 2_000, 42))
    ring = generate_experiment(ExperimentConfig(ScenarioKind.RING, 2_000, 42))
    sphere = generate_experiment(ExperimentConfig(ScenarioKind.SPHERE, 2_000, 42))
    collision = generate_experiment(ExperimentConfig(ScenarioKind.HEAD_ON_COLLISION, 2_000, 42))

    disk_radius = np.hypot(disk.state.positions[:, 0], disk.state.positions[:, 2])
    ring_radius = np.hypot(ring.state.positions[:, 0], ring.state.positions[:, 2])
    assert np.std(disk.state.positions[:, 1]) < 0.12
    assert np.quantile(disk_radius, 0.90) > np.quantile(disk_radius, 0.50) * 1.25
    assert np.std(ring_radius) < 0.60
    assert np.quantile(ring_radius, 0.10) > 4.4
    assert np.std(sphere.state.positions[:, 1]) > 1.8
    assert np.quantile(np.abs(collision.state.positions[:, 0]), 0.50) > 5.0


def test_head_on_centres_move_toward_one_another_and_chaos_is_hotter_than_bound_cloud() -> None:
    collision = generate_experiment(ExperimentConfig(ScenarioKind.HEAD_ON_COLLISION, 2_000, 777))
    left = collision.state.positions[:, 0] < 0.0
    assert np.mean(collision.state.velocities[left, 0]) > 0.10
    assert np.mean(collision.state.velocities[~left, 0]) < -0.10

    bound = generate_experiment(ExperimentConfig(ScenarioKind.RANDOM_BOUND, 2_000, 777))
    chaos = generate_experiment(ExperimentConfig(ScenarioKind.TOTAL_CHAOS, 2_000, 777))
    assert kinetic_energy(chaos.state) > 5.0 * kinetic_energy(bound.state)


def test_spiral_keeps_its_analytic_halo_while_free_scenarios_do_not() -> None:
    spiral = generate_experiment(ExperimentConfig(ScenarioKind.SPIRAL_GALAXY, 400, 3))
    cloud = generate_experiment(ExperimentConfig(ScenarioKind.RANDOM_BOUND, 400, 3))
    assert len(spiral.external_fields) == 1
    assert cloud.external_fields == ()


def test_public_generator_rejects_the_wrong_contract() -> None:
    with pytest.raises(TypeError):
        generate_experiment(object())  # type: ignore[arg-type]
