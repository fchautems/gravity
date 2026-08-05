from __future__ import annotations

import logging
import time
from collections.abc import Callable

import numpy as np
import pytest

from gravity.app.physics_worker import (
    EXACT_PARTICLE_LIMIT,
    PhysicsWorker,
    SimulationWorkerError,
)
from gravity.core.experiment import ExperimentConfig, ScenarioKind
from gravity.core.simulation import RenderSnapshot, SolverMode
from gravity.core.state import FloatArray


class ZeroGravitySolver:
    name = "zero"

    def compute(
        self,
        positions: FloatArray,
        masses: FloatArray,
        softening: float,
        output_buffer: FloatArray | None = None,
    ) -> FloatArray:
        del masses, softening
        output = np.zeros_like(positions) if output_buffer is None else output_buffer
        output.fill(0.0)
        return output


def _wait_for(
    worker: PhysicsWorker,
    predicate: Callable[[RenderSnapshot], bool],
    *,
    timeout: float = 3.0,
) -> RenderSnapshot:
    deadline = time.monotonic() + timeout
    latest = None
    while time.monotonic() < deadline:
        worker.raise_if_failed()
        candidate = worker.latest_snapshot()
        if candidate is not None:
            latest = candidate
            if predicate(candidate):
                return candidate
        time.sleep(0.005)
    raise AssertionError(f"snapshot condition was not reached; latest={latest}")


def test_worker_defaults_to_barnes_hut_and_exact_requires_explicit_command() -> None:
    worker = PhysicsWorker(
        logging.getLogger("worker-test"),
        solver_factory=lambda _mode: ZeroGravitySolver(),
        barnes_hut_particles=120,
        exact_particles=100,
    )
    worker.start()
    try:
        initial = worker.wait_for_snapshot()
        assert initial.status.solver_mode is SolverMode.BARNES_HUT
        assert initial.status.particle_count == 120
        assert initial.status.paused
        assert initial.status.step_count == 0
        assert initial.positions.dtype == np.float32
        assert not initial.positions.flags.writeable
        assert initial.observations is not None
        assert initial.observations.stats.ejected_count >= 0

        worker.pause()
        paused = _wait_for(worker, lambda item: item.status.paused)
        paused_generation = paused.status.generation

        worker.set_solver(SolverMode.EXACT)
        exact = _wait_for(
            worker,
            lambda item: item.status.solver_mode is SolverMode.EXACT,
        )
        assert exact.status.particle_count == 100
        assert exact.status.generation == paused_generation + 1
        assert exact.status.paused
        assert exact.status.step_count == 0

        worker.single_step()
        stepped = _wait_for(worker, lambda item: item.status.step_count == 1)
        assert stepped.status.paused
        assert stepped.status.simulation_time > 0.0

        worker.reset()
        reset = _wait_for(
            worker,
            lambda item: item.status.generation == exact.status.generation + 1,
        )
        assert reset.status.step_count == 0
        assert reset.status.paused

        worker.set_time_scale(1.5)
        sped_up = _wait_for(worker, lambda item: item.status.time_scale == 1.5)
        assert sped_up.status.solver_mode is SolverMode.EXACT
    finally:
        worker.shutdown()
    assert not worker.running


def test_exact_particle_limit_is_a_hard_construction_guard() -> None:
    with pytest.raises(ValueError, match=str(EXACT_PARTICLE_LIMIT)):
        PhysicsWorker(
            logging.getLogger("worker-limit-test"),
            exact_particles=EXACT_PARTICLE_LIMIT + 1,
        )


def test_worker_failure_is_relayed_instead_of_disappearing() -> None:
    def fail(_config: object) -> object:
        raise RuntimeError("scenario failure")

    worker = PhysicsWorker(
        logging.getLogger("worker-failure-test"),
        scenario_factory=fail,  # type: ignore[arg-type]
        barnes_hut_particles=100,
        exact_particles=100,
    )
    worker.start()
    try:
        with pytest.raises(SimulationWorkerError) as captured:
            worker.wait_for_snapshot(timeout=1.0)
        assert isinstance(captured.value.__cause__, RuntimeError)
    finally:
        worker.shutdown()


def test_worker_applies_reproducible_experiments_and_restores_full_count_after_exact() -> None:
    worker = PhysicsWorker(
        logging.getLogger("worker-experiment-test"),
        solver_factory=lambda _mode: ZeroGravitySolver(),
        barnes_hut_particles=300,
        exact_particles=200,
    )
    worker.start()
    try:
        worker.wait_for_snapshot()
        worker.pause()
        _wait_for(worker, lambda item: item.status.paused)
        experiment = ExperimentConfig(ScenarioKind.RING, 300, 99)
        worker.set_experiment(experiment)
        ring = _wait_for(
            worker,
            lambda item: item.status.experiment == experiment,
        )
        assert ring.status.particle_count == 300
        assert ring.status.step_count == 0
        initial_ring_positions = ring.positions.copy()

        worker.reset()
        repeated = _wait_for(
            worker,
            lambda item: item.status.generation == ring.status.generation + 1,
        )
        np.testing.assert_array_equal(repeated.positions, initial_ring_positions)

        worker.set_experiment(ExperimentConfig(ScenarioKind.RING, 300, 100))
        rerolled = _wait_for(
            worker,
            lambda item: item.status.experiment is not None and item.status.experiment.seed == 100,
        )
        assert not np.array_equal(rerolled.positions, initial_ring_positions)

        worker.set_solver(SolverMode.EXACT)
        exact = _wait_for(worker, lambda item: item.status.solver_mode is SolverMode.EXACT)
        assert exact.status.particle_count == 200
        assert exact.status.experiment == ExperimentConfig(ScenarioKind.RING, 300, 100)

        worker.set_solver(SolverMode.BARNES_HUT)
        restored = _wait_for(
            worker,
            lambda item: item.status.solver_mode is SolverMode.BARNES_HUT,
        )
        assert restored.status.particle_count == 300
        assert restored.status.experiment == exact.status.experiment
        assert restored.status.paused
    finally:
        worker.shutdown()
