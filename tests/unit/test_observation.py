from __future__ import annotations

import numpy as np

from gravity.core.observation import initial_ejection_radius, observe_particles
from gravity.core.state import ParticleState


def test_observation_classifies_only_distant_outgoing_unbound_particles() -> None:
    positions = np.array(
        [[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [-20.0, 0.0, 0.0], [20.0, 0.0, 0.0]],
        dtype=np.float64,
    )
    velocities = np.array(
        [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        dtype=np.float64,
    )
    state = ParticleState.from_arrays(positions, velocities, np.full(4, 0.25))
    observed = observe_particles(
        state,
        np.array([0, 1, 2, 0], dtype=np.uint8),
        (),
        softening=0.08,
        ejection_radius=10.0,
        reference_energy=None,
    )
    np.testing.assert_array_equal(observed.ejected, [False, False, True, True])
    assert observed.stats.ejected_count == 2
    assert observed.stats.center_of_mass == (0.0, 0.0, 0.0)
    assert not observed.radii.flags.writeable


def test_initial_ejection_boundary_scales_with_the_starting_cloud() -> None:
    state = ParticleState.from_arrays(
        [[-2.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
        [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
        [0.5, 0.5],
    )
    assert initial_ejection_radius(state) == 12.0
