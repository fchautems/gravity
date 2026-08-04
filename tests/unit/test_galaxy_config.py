from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from gravity.scenarios import GalaxyComponent, GalaxyConfig, GalaxyMassModel, generate_spiral_galaxy


def test_default_configuration_allocates_every_live_component() -> None:
    config = GalaxyConfig()
    assert config.particle_count == 10_000
    assert config.disk_particle_count == 8_399
    assert config.bulge_particle_count == 1_600
    assert config.central_particle_count == 1
    assert config.disk_particle_count + config.bulge_particle_count + 1 == 10_000
    assert config.live_mass == pytest.approx(0.82)


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"particle_count": 99}, ValueError),
        ({"particle_count": 50_001}, ValueError),
        ({"particle_count": True}, TypeError),
        ({"seed": -1}, ValueError),
        ({"seed": 2**32}, ValueError),
        ({"seed": 1.5}, TypeError),
        ({"disk_mass": 0.0}, ValueError),
        ({"bulge_mass": float("nan")}, ValueError),
        ({"central_mass": -0.1}, ValueError),
        ({"halo_mass": float("inf")}, ValueError),
        ({"disk_outer_radius": 3.0}, ValueError),
        ({"disk_outer_radius": 25.0}, ValueError),
        ({"bulge_outer_radius": 0.5}, ValueError),
        ({"bulge_particle_fraction": 0.0}, ValueError),
        ({"bulge_particle_fraction": 1.0}, ValueError),
        ({"arm_count": 0}, ValueError),
        ({"arm_count": 9}, ValueError),
        ({"spiral_fraction": 1.1}, ValueError),
        ({"spiral_winding": float("nan")}, ValueError),
        ({"spiral_scatter": -0.1}, ValueError),
        ({"disk_velocity_dispersion": 1.1}, ValueError),
        ({"vertical_velocity_dispersion": -0.1}, ValueError),
        ({"bulge_velocity_scale": float("inf")}, ValueError),
        ({"softening": 0.0}, ValueError),
        ({"softening": 0.3}, ValueError),
        ({"time_step": 0.0}, ValueError),
        ({"time_step": 0.1}, ValueError),
    ],
)
def test_invalid_configuration_boundaries_are_rejected(
    changes: dict[str, object],
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        replace(GalaxyConfig(), **changes)


def test_zero_central_and_halo_masses_are_supported_explicitly() -> None:
    config = GalaxyConfig(particle_count=100, central_mass=0.0, halo_mass=0.0)
    assert config.central_particle_count == 0
    assert config.noncentral_particle_count == config.particle_count
    assert config.disk_particle_count + config.bulge_particle_count == config.particle_count
    assert np.array_equal(
        GalaxyMassModel(config).halo.enclosed_mass(np.array([0.0, 1.0])),
        np.zeros(2),
    )
    galaxy = generate_spiral_galaxy(config)
    assert not np.any(galaxy.components == GalaxyComponent.CENTRAL.value)
    assert float(np.sum(galaxy.state.masses)) == pytest.approx(
        config.disk_mass + config.bulge_mass,
        abs=2e-15,
    )


def test_mass_curve_is_monotonic_bounded_and_circularly_consistent() -> None:
    model = GalaxyMassModel(GalaxyConfig())
    radius = np.linspace(0.0, 30.0, 1_001)
    enclosed = model.total_enclosed_mass(radius)
    acceleration = model.radial_acceleration(radius)
    speed = model.circular_speed(radius)
    assert enclosed[0] == 0.0
    assert np.all(np.diff(enclosed) >= -1e-15)
    assert enclosed[-1] < model.config.live_mass + model.config.halo_mass
    assert acceleration[0] == 0.0
    np.testing.assert_allclose(speed * speed, -radius * acceleration, rtol=2e-15, atol=1e-16)


@pytest.mark.parametrize("radius", [[-1.0], [float("nan")], [float("inf")]])
def test_mass_curve_rejects_invalid_radii(radius: list[float]) -> None:
    with pytest.raises(ValueError):
        GalaxyMassModel(GalaxyConfig()).total_enclosed_mass(radius)
