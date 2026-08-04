from __future__ import annotations

import numpy as np
import pytest

from gravity.core.state import ParticleState


def _valid_state() -> ParticleState:
    return ParticleState.from_arrays(
        positions=[[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        velocities=[[0.0, -0.5, 0.0], [0.0, 0.5, 0.0]],
        masses=[0.5, 0.5],
        ids=[7, 9],
    )


def test_factory_builds_the_strict_structure_of_arrays_contract() -> None:
    state = _valid_state()
    assert state.particle_count == 2
    assert state.positions.shape == (2, 3)
    assert state.velocities.shape == (2, 3)
    assert state.accelerations.shape == (2, 3)
    assert state.masses.shape == (2,)
    assert state.ids.shape == (2,)
    assert state.positions.dtype == np.float64
    assert state.velocities.dtype == np.float64
    assert state.accelerations.dtype == np.float64
    assert state.masses.dtype == np.float64
    assert state.ids.dtype == np.uint64
    assert state.positions.flags.c_contiguous
    assert state.velocities.flags.c_contiguous
    assert state.accelerations.flags.c_contiguous
    assert state.masses.flags.c_contiguous
    assert np.array_equal(state.ids, [7, 9])
    assert not state.accelerations_valid


def test_factory_copies_inputs_and_generates_stable_ids() -> None:
    positions = np.zeros((2, 3), dtype=np.float32)
    state = ParticleState.from_arrays(positions, np.zeros((2, 3)), [1.0, 2.0])
    positions[0, 0] = 99.0
    assert state.positions[0, 0] == 0.0
    assert np.array_equal(state.ids, np.array([0, 1], dtype=np.uint64))


def test_copy_is_independent_and_preserves_progress_flags() -> None:
    state = _valid_state()
    state.mark_accelerations_valid()
    state.simulation_time = 2.5
    state.step_count = 4
    clone = state.copy()
    clone.positions[0, 0] = 12.0
    clone.accelerations[0, 0] = 3.0
    assert state.positions[0, 0] == -1.0
    assert state.accelerations[0, 0] == 0.0
    assert clone.accelerations_valid
    assert clone.simulation_time == 2.5
    assert clone.step_count == 4
    clone.invalidate_accelerations()
    assert not clone.accelerations_valid


@pytest.mark.parametrize(
    ("positions", "velocities", "masses", "ids", "error"),
    [
        ([], [], [], None, ValueError),
        ([[0.0, 0.0]], [[0.0, 0.0, 0.0]], [1.0], None, ValueError),
        ([[0.0, 0.0, 0.0]], [[0.0, 0.0]], [1.0], None, ValueError),
        ([[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [], None, ValueError),
        ([[np.nan, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [1.0], None, ValueError),
        ([[0.0, 0.0, 0.0]], [[np.inf, 0.0, 0.0]], [1.0], None, ValueError),
        ([[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [0.0], None, ValueError),
        ([[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [-1.0], None, ValueError),
        ([[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [1.0], [-1], ValueError),
        ([[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [1.0], [1.5], TypeError),
    ],
)
def test_factory_rejects_invalid_boundaries(
    positions: object,
    velocities: object,
    masses: object,
    ids: object,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        ParticleState.from_arrays(positions, velocities, masses, ids=ids)


def test_validation_detects_corruption_after_creation() -> None:
    state = _valid_state()
    state.masses[0] = -1.0
    with pytest.raises(ValueError, match="strictly positive"):
        state.validate()


def test_direct_constructor_rejects_wrong_dtypes_and_duplicate_ids() -> None:
    state = _valid_state()
    with pytest.raises(TypeError, match="float64"):
        ParticleState(
            state.positions.astype(np.float32),
            state.velocities.copy(),
            state.accelerations.copy(),
            state.masses.copy(),
            state.ids.copy(),
        )
    with pytest.raises(ValueError, match="unique"):
        ParticleState(
            state.positions.copy(),
            state.velocities.copy(),
            state.accelerations.copy(),
            state.masses.copy(),
            np.array([4, 4], dtype=np.uint64),
        )
