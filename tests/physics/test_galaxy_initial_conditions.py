from __future__ import annotations

import numpy as np
import pytest

from gravity.physics import (
    CompositeGravitySolver,
    ExactGravitySolver,
    LeapfrogIntegrator,
    center_of_mass,
    total_momentum,
)
from gravity.scenarios import (
    GalaxyComponent,
    GalaxyConfig,
    GalaxyInitialConditions,
    generate_spiral_galaxy,
)


def _component_mask(galaxy: GalaxyInitialConditions, component: GalaxyComponent) -> np.ndarray:
    return galaxy.components == component.value


def test_default_galaxy_is_exactly_reproducible_and_state_ready() -> None:
    first = generate_spiral_galaxy()
    second = generate_spiral_galaxy()
    assert np.array_equal(first.state.positions, second.state.positions)
    assert np.array_equal(first.state.velocities, second.state.velocities)
    assert np.array_equal(first.state.masses, second.state.masses)
    assert np.array_equal(first.components, second.components)
    assert first.state.particle_count == 10_000
    assert first.state.positions.dtype == np.float64
    assert first.state.positions.flags.c_contiguous
    assert first.state.velocities.flags.c_contiguous
    assert first.state.masses.flags.c_contiguous
    assert not first.components.flags.writeable
    first.state.validate()


def test_different_seed_changes_the_state_without_changing_component_totals() -> None:
    first = generate_spiral_galaxy(GalaxyConfig(particle_count=1_000, seed=1))
    second = generate_spiral_galaxy(GalaxyConfig(particle_count=1_000, seed=2))
    assert not np.array_equal(first.state.positions, second.state.positions)
    assert not np.array_equal(first.state.velocities, second.state.velocities)
    assert np.bincount(first.components).tolist() == np.bincount(second.components).tolist()


def test_component_counts_masses_center_and_bulk_velocity_match_configuration() -> None:
    galaxy = generate_spiral_galaxy()
    config = galaxy.config
    state = galaxy.state
    disk = _component_mask(galaxy, GalaxyComponent.DISK)
    bulge = _component_mask(galaxy, GalaxyComponent.BULGE)
    central = _component_mask(galaxy, GalaxyComponent.CENTRAL)
    assert np.count_nonzero(disk) == config.disk_particle_count
    assert np.count_nonzero(bulge) == config.bulge_particle_count
    assert np.count_nonzero(central) == config.central_particle_count
    assert float(np.sum(state.masses[disk])) == pytest.approx(config.disk_mass, abs=2e-15)
    assert float(np.sum(state.masses[bulge])) == pytest.approx(config.bulge_mass, abs=2e-15)
    assert float(np.sum(state.masses[central])) == pytest.approx(config.central_mass, abs=2e-15)
    assert np.linalg.norm(center_of_mass(state)) <= 5e-15
    assert np.linalg.norm(total_momentum(state)) <= 5e-15
    np.testing.assert_array_equal(state.positions[central], np.zeros((1, 3)))
    np.testing.assert_array_equal(state.velocities[central], np.zeros((1, 3)))


def test_disk_and_bulge_follow_the_documented_seeded_distributions() -> None:
    galaxy = generate_spiral_galaxy()
    disk_positions = galaxy.state.positions[_component_mask(galaxy, GalaxyComponent.DISK)]
    disk_radius = np.hypot(disk_positions[:, 0], disk_positions[:, 2])
    bulge_positions = galaxy.state.positions[_component_mask(galaxy, GalaxyComponent.BULGE)]
    bulge_radius = np.linalg.norm(bulge_positions, axis=1)
    np.testing.assert_allclose(
        np.quantile(disk_radius, [0.1, 0.5, 0.9]),
        [1.0361, 3.3321, 7.3290],
        rtol=0.015,
        atol=0.02,
    )
    assert np.std(disk_positions[:, 1]) == pytest.approx(
        galaxy.config.disk_scale_height,
        rel=0.08,
    )
    assert np.quantile(bulge_radius, 0.5) < 0.35 * np.quantile(disk_radius, 0.5)
    assert np.quantile(bulge_radius, 0.99) <= galaxy.config.bulge_outer_radius * 1.02


def test_disk_velocity_is_tangential_coherent_and_matches_the_rotation_curve() -> None:
    galaxy = generate_spiral_galaxy()
    disk = _component_mask(galaxy, GalaxyComponent.DISK)
    positions = galaxy.state.positions[disk]
    velocities = galaxy.state.velocities[disk]
    radius = np.hypot(positions[:, 0], positions[:, 2])
    radial = np.column_stack(
        (
            positions[:, 0] / radius,
            np.zeros_like(radius),
            positions[:, 2] / radius,
        )
    )
    tangential = np.column_stack((-radial[:, 2], np.zeros_like(radius), radial[:, 0]))
    radial_speed = np.sum(velocities * radial, axis=1)
    tangential_speed = np.sum(velocities * tangential, axis=1)
    expected_speed = galaxy.mass_model.circular_speed(radius)
    assert np.mean(tangential_speed > 0.0) >= 0.999
    assert np.median(np.abs(radial_speed / tangential_speed)) < 0.04
    assert np.median(np.abs(velocities[:, 1] / tangential_speed)) < 0.025
    assert np.median(np.abs(tangential_speed / expected_speed - 1.0)) < 0.03


def test_small_exact_galaxy_rotates_without_prompt_radial_collapse() -> None:
    config = GalaxyConfig(
        particle_count=240,
        seed=1_234,
        spiral_fraction=0.0,
        disk_velocity_dispersion=0.0,
        vertical_velocity_dispersion=0.0,
    )
    galaxy = generate_spiral_galaxy(config)
    disk = _component_mask(galaxy, GalaxyComponent.DISK)
    initial_positions = galaxy.state.positions[disk].copy()
    initial_radius = np.hypot(initial_positions[:, 0], initial_positions[:, 2])
    initial_angle = np.arctan2(initial_positions[:, 2], initial_positions[:, 0])
    solver = CompositeGravitySolver(ExactGravitySolver(), (galaxy.mass_model.halo,))
    LeapfrogIntegrator(solver, config.time_step, config.softening).step(galaxy.state, steps=200)

    final_positions = galaxy.state.positions[disk]
    final_radius = np.hypot(final_positions[:, 0], final_positions[:, 2])
    final_angle = np.arctan2(final_positions[:, 2], final_positions[:, 0])
    angular_travel = np.angle(np.exp(1j * (final_angle - initial_angle)))
    radius_ratio = final_radius / initial_radius
    assert np.median(angular_travel) > 0.35
    assert np.quantile(radius_ratio, 0.10) > 0.80
    assert np.quantile(radius_ratio, 0.90) < 1.20
    assert np.mean(radius_ratio < 0.5) < 0.03


def test_generator_and_initial_condition_boundaries_are_validated() -> None:
    with pytest.raises(TypeError):
        generate_spiral_galaxy(object())  # type: ignore[arg-type]
    galaxy = generate_spiral_galaxy(GalaxyConfig(particle_count=100))
    invalid_components = galaxy.components.copy()
    invalid_components[0] = 99
    with pytest.raises(ValueError, match="unknown"):
        GalaxyInitialConditions(
            state=galaxy.state,
            components=invalid_components,
            config=galaxy.config,
            mass_model=galaxy.mass_model,
        )
    wrong_counts = galaxy.components.copy()
    wrong_counts[wrong_counts == GalaxyComponent.BULGE.value] = GalaxyComponent.DISK.value
    with pytest.raises(ValueError, match="component count"):
        GalaxyInitialConditions(
            state=galaxy.state,
            components=wrong_counts,
            config=galaxy.config,
            mass_model=galaxy.mass_model,
        )
    with pytest.raises(ValueError, match="mass model"):
        GalaxyInitialConditions(
            state=galaxy.state,
            components=galaxy.components.copy(),
            config=galaxy.config,
            mass_model=generate_spiral_galaxy(
                GalaxyConfig(particle_count=100, seed=999)
            ).mass_model,
        )
