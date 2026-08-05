from __future__ import annotations

from gravity.app.graphics_app import _dispatch_simulation_actions
from gravity.core.experiment import ExperimentConfig, ScenarioKind
from gravity.core.simulation import SimulationStatus, SolverMode
from gravity.ui.panel import UiActions


class RecordingWorker:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def pause(self) -> None:
        self.calls.append("pause")

    def resume(self) -> None:
        self.calls.append("resume")

    def reset(self) -> None:
        self.calls.append("reset")

    def single_step(self) -> None:
        self.calls.append("step")

    def set_time_scale(self, value: float) -> None:
        self.calls.append(("speed", value))

    def set_solver(self, mode: SolverMode) -> None:
        self.calls.append(("solver", mode))

    def set_experiment(self, experiment: ExperimentConfig) -> None:
        self.calls.append(("experiment", experiment))


def _status(*, paused: bool) -> SimulationStatus:
    return SimulationStatus(
        solver_mode=SolverMode.BARNES_HUT,
        particle_count=10_000,
        simulation_time=0.0,
        step_count=0,
        generation=0,
        paused=paused,
        time_scale=1.0,
        physics_seconds=0.0,
    )


def test_controller_translates_all_ui_actions_without_ui_calling_physics() -> None:
    worker = RecordingWorker()
    experiment = ExperimentConfig(ScenarioKind.RING, 2_000, 12)
    actions = UiActions(
        toggle_pause=True,
        reset_simulation=True,
        single_step=True,
        time_scale=1.5,
        solver_mode=SolverMode.EXACT,
        experiment=experiment,
    )
    _dispatch_simulation_actions(worker, _status(paused=False), actions)  # type: ignore[arg-type]
    assert worker.calls == [
        ("solver", SolverMode.EXACT),
        ("experiment", experiment),
        "pause",
        "reset",
        "step",
        ("speed", 1.5),
    ]

    worker.calls.clear()
    _dispatch_simulation_actions(  # type: ignore[arg-type]
        worker,
        _status(paused=True),
        UiActions(toggle_pause=True),
    )
    assert worker.calls == ["resume"]


def test_start_and_stop_are_unambiguous_transport_actions() -> None:
    worker = RecordingWorker()
    _dispatch_simulation_actions(  # type: ignore[arg-type]
        worker,
        _status(paused=True),
        UiActions(start_simulation=True),
    )
    assert worker.calls == ["resume"]

    worker.calls.clear()
    _dispatch_simulation_actions(  # type: ignore[arg-type]
        worker,
        _status(paused=False),
        UiActions(stop_simulation=True),
    )
    assert worker.calls == ["pause", "reset"]
