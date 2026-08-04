from __future__ import annotations

import numpy as np
import pytest

from gravity.core.simulation import RenderSnapshot, SimulationStatus, SolverMode


def _status(**changes: object) -> SimulationStatus:
    values: dict[str, object] = {
        "solver_mode": SolverMode.BARNES_HUT,
        "particle_count": 4,
        "simulation_time": 0.5,
        "step_count": 25,
        "generation": 1,
        "paused": False,
        "time_scale": 1.0,
        "physics_seconds": 0.012,
    }
    values.update(changes)
    return SimulationStatus(**values)  # type: ignore[arg-type]


def test_snapshot_is_contiguous_float32_and_becomes_read_only() -> None:
    positions = np.zeros((4, 3), dtype=np.float32)
    snapshot = RenderSnapshot(positions, _status())
    assert not snapshot.positions.flags.writeable
    assert snapshot.status.physics_ms == pytest.approx(12.0)
    assert snapshot.status.solver_mode.french_name == "Barnes–Hut"
    assert snapshot.status.effective_time_scale == pytest.approx(1.0)


def test_effective_speed_reports_the_compute_ceiling() -> None:
    status = _status(time_scale=2.0, time_step=0.02, physics_seconds=0.04)
    assert status.effective_time_scale == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("positions", "error"),
    [
        (np.zeros((4, 3), dtype=np.float64), TypeError),
        (np.zeros((3, 3), dtype=np.float32), ValueError),
        (np.full((4, 3), np.nan, dtype=np.float32), ValueError),
    ],
)
def test_snapshot_rejects_invalid_render_arrays(
    positions: np.ndarray, error: type[Exception]
) -> None:
    with pytest.raises(error):
        RenderSnapshot(positions, _status())


@pytest.mark.parametrize(
    "changes",
    [
        {"particle_count": 0},
        {"step_count": -1},
        {"generation": -1},
        {"simulation_time": float("nan")},
        {"physics_seconds": -0.1},
        {"time_scale": 0.0},
    ],
)
def test_status_rejects_invalid_values(changes: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        _status(**changes)
