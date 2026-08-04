from __future__ import annotations

import numpy as np

from gravity.physics import BarnesHutSolver, CompositeGravitySolver, LeapfrogIntegrator
from gravity.scenarios import GalaxyConfig, generate_spiral_galaxy


def test_barnes_hut_composes_with_halo_and_leapfrog_without_special_cases() -> None:
    galaxy = generate_spiral_galaxy(GalaxyConfig(particle_count=300, seed=5678))
    solver = BarnesHutSolver(theta=0.7)
    composite = CompositeGravitySolver(solver, (galaxy.mass_model.halo,))
    integrator = LeapfrogIntegrator(composite, galaxy.config.time_step, galaxy.config.softening)
    initial_positions = galaxy.state.positions.copy()
    integrator.step(galaxy.state, steps=4)

    assert galaxy.state.step_count == 4
    assert galaxy.state.simulation_time == 4 * galaxy.config.time_step
    assert np.all(np.isfinite(galaxy.state.positions))
    assert np.all(np.isfinite(galaxy.state.velocities))
    assert not np.array_equal(galaxy.state.positions, initial_positions)
    assert solver.last_stats is not None
