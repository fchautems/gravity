"""Fixed-step physics worker and bounded render-snapshot exchange."""

from __future__ import annotations

import logging
import math
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from time import perf_counter

import numpy as np

from gravity.core.simulation import RenderSnapshot, SimulationStatus, SolverMode
from gravity.physics import (
    AccelerationSolver,
    BarnesHutSolver,
    CompositeGravitySolver,
    ExactGravitySolver,
    LeapfrogIntegrator,
)
from gravity.scenarios import GalaxyConfig, GalaxyInitialConditions, generate_spiral_galaxy

DEFAULT_INTERACTIVE_PARTICLES = 10_000
EXACT_PARTICLE_LIMIT = 1_000
MIN_TIME_SCALE = 0.1
MAX_TIME_SCALE = 2.5
MAX_SCHEDULE_LAG_STEPS = 4
WORKER_JOIN_TIMEOUT = 5.0

type ScenarioFactory = Callable[[GalaxyConfig], GalaxyInitialConditions]
type SolverFactory = Callable[[SolverMode], AccelerationSolver]


class SimulationWorkerError(RuntimeError):
    """Failure raised in the worker and relayed to the application thread."""


class _CommandKind(Enum):
    PAUSE = auto()
    RESUME = auto()
    SINGLE_STEP = auto()
    RESET = auto()
    SET_TIME_SCALE = auto()
    SET_SOLVER = auto()
    STOP = auto()


@dataclass(frozen=True, slots=True)
class _Command:
    kind: _CommandKind
    value: float | SolverMode | None = None


@dataclass(slots=True)
class _Runtime:
    galaxy: GalaxyInitialConditions
    self_gravity: AccelerationSolver
    integrator: LeapfrogIntegrator
    solver_mode: SolverMode
    generation: int
    paused: bool
    time_scale: float
    physics_seconds: float = 0.0


def _default_solver_factory(mode: SolverMode) -> AccelerationSolver:
    if mode is SolverMode.BARNES_HUT:
        return BarnesHutSolver()
    return ExactGravitySolver()


def _validate_particle_count(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if not 100 <= value <= 50_000:
        raise ValueError(f"{name} must be between 100 and 50,000")
    return value


def _validate_time_scale(value: float) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError) as error:
        raise TypeError("time_scale must be a real number") from error
    if not math.isfinite(converted) or not MIN_TIME_SCALE <= converted <= MAX_TIME_SCALE:
        raise ValueError(f"time_scale must be between {MIN_TIME_SCALE} and {MAX_TIME_SCALE}")
    return converted


class PhysicsWorker:
    """Own mutable physics state and publish complete copies without blocking rendering."""

    def __init__(
        self,
        logger: logging.Logger,
        *,
        scenario_factory: ScenarioFactory = generate_spiral_galaxy,
        solver_factory: SolverFactory = _default_solver_factory,
        barnes_hut_particles: int = DEFAULT_INTERACTIVE_PARTICLES,
        exact_particles: int = EXACT_PARTICLE_LIMIT,
    ) -> None:
        self._logger = logger
        self._scenario_factory = scenario_factory
        self._solver_factory = solver_factory
        self._barnes_hut_particles = _validate_particle_count(
            barnes_hut_particles, "barnes_hut_particles"
        )
        self._exact_particles = _validate_particle_count(exact_particles, "exact_particles")
        if self._exact_particles > EXACT_PARTICLE_LIMIT:
            raise ValueError(f"exact_particles cannot exceed {EXACT_PARTICLE_LIMIT}")

        self._commands: queue.Queue[_Command] = queue.Queue()
        self._snapshots: queue.Queue[RenderSnapshot] = queue.Queue(maxsize=1)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._failure_lock = threading.Lock()
        self._failure: BaseException | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("physics worker can only be started once")
        self._thread = threading.Thread(
            target=self._run_guarded,
            name="GravityPhysics",
            daemon=True,
        )
        self._thread.start()

    def pause(self) -> None:
        self._send(_CommandKind.PAUSE)

    def resume(self) -> None:
        self._send(_CommandKind.RESUME)

    def single_step(self) -> None:
        self._send(_CommandKind.SINGLE_STEP)

    def reset(self) -> None:
        self._send(_CommandKind.RESET)

    def set_time_scale(self, value: float) -> None:
        self._commands.put(_Command(_CommandKind.SET_TIME_SCALE, _validate_time_scale(value)))

    def set_solver(self, mode: SolverMode) -> None:
        if not isinstance(mode, SolverMode):
            raise TypeError("mode must be a SolverMode")
        self._commands.put(_Command(_CommandKind.SET_SOLVER, mode))

    def stop(self) -> None:
        self._stop_event.set()
        self._commands.put(_Command(_CommandKind.STOP))

    def shutdown(self) -> None:
        """Request shutdown and wait a bounded time for the worker to finish."""

        self.stop()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(WORKER_JOIN_TIMEOUT)
            if thread.is_alive():
                raise SimulationWorkerError("Le moteur physique ne s'est pas arrêté proprement.")

    def wait_for_snapshot(self, timeout: float = 20.0) -> RenderSnapshot:
        """Wait for the initial complete snapshot without hiding worker failures."""

        deadline = perf_counter() + timeout
        while True:
            self.raise_if_failed()
            remaining = deadline - perf_counter()
            if remaining <= 0.0:
                raise SimulationWorkerError("Le moteur physique n'a pas démarré à temps.")
            try:
                return self._snapshots.get(timeout=min(remaining, 0.05))
            except queue.Empty:
                continue

    def latest_snapshot(self) -> RenderSnapshot | None:
        """Return only the newest available snapshot, never waiting for physics."""

        latest = None
        while True:
            try:
                latest = self._snapshots.get_nowait()
            except queue.Empty:
                return latest

    def raise_if_failed(self) -> None:
        with self._failure_lock:
            failure = self._failure
        if failure is not None:
            raise SimulationWorkerError(
                "Le calcul physique a été mis en pause après une erreur interne."
            ) from failure

    def _send(self, kind: _CommandKind) -> None:
        self._commands.put(_Command(kind))

    def _run_guarded(self) -> None:
        try:
            self._run()
        except BaseException as error:  # noqa: BLE001 - thread exception boundary
            with self._failure_lock:
                self._failure = error
            self._stop_event.set()
            self._logger.exception("Physics worker failed")

    def _particle_count(self, mode: SolverMode) -> int:
        if mode is SolverMode.BARNES_HUT:
            return self._barnes_hut_particles
        return self._exact_particles

    def _create_runtime(
        self,
        mode: SolverMode,
        *,
        generation: int,
        paused: bool,
        time_scale: float,
    ) -> _Runtime:
        config = GalaxyConfig(particle_count=self._particle_count(mode))
        galaxy = self._scenario_factory(config)
        self_gravity = self._solver_factory(mode)
        solver = CompositeGravitySolver(self_gravity, (galaxy.mass_model.halo,))
        integrator = LeapfrogIntegrator(solver, config.time_step, config.softening)
        self._logger.info(
            "Physics generation %s ready: solver=%s, particles=%s, dt=%s",
            generation,
            mode.value,
            config.particle_count,
            config.time_step,
        )
        return _Runtime(
            galaxy=galaxy,
            self_gravity=self_gravity,
            integrator=integrator,
            solver_mode=mode,
            generation=generation,
            paused=paused,
            time_scale=time_scale,
        )

    def _publish(self, runtime: _Runtime) -> None:
        state = runtime.galaxy.state
        positions = np.ascontiguousarray(state.positions, dtype=np.float32)
        status = SimulationStatus(
            solver_mode=runtime.solver_mode,
            particle_count=state.particle_count,
            simulation_time=state.simulation_time,
            step_count=state.step_count,
            generation=runtime.generation,
            paused=runtime.paused,
            time_scale=runtime.time_scale,
            physics_seconds=runtime.physics_seconds,
        )
        snapshot = RenderSnapshot(positions, status)
        try:
            self._snapshots.get_nowait()
        except queue.Empty:
            pass
        try:
            self._snapshots.put_nowait(snapshot)
        except queue.Full:  # a newer consumer race can only make dropping safe
            pass

    def _advance_once(self, runtime: _Runtime) -> None:
        started = perf_counter()
        runtime.integrator.step(runtime.galaxy.state)
        runtime.physics_seconds = perf_counter() - started
        self._publish(runtime)

    def _handle_command(self, runtime: _Runtime, command: _Command) -> _Runtime | None:
        if command.kind is _CommandKind.STOP:
            return None
        if command.kind is _CommandKind.PAUSE:
            runtime.paused = True
            self._publish(runtime)
        elif command.kind is _CommandKind.RESUME:
            runtime.paused = False
            self._publish(runtime)
        elif command.kind is _CommandKind.SINGLE_STEP:
            if runtime.paused:
                self._advance_once(runtime)
        elif command.kind is _CommandKind.RESET:
            runtime = self._create_runtime(
                runtime.solver_mode,
                generation=runtime.generation + 1,
                paused=runtime.paused,
                time_scale=runtime.time_scale,
            )
            self._publish(runtime)
        elif command.kind is _CommandKind.SET_TIME_SCALE:
            value = command.value
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError("SET_TIME_SCALE requires a real number")
            runtime.time_scale = _validate_time_scale(value)
            self._publish(runtime)
        elif command.kind is _CommandKind.SET_SOLVER:
            mode = command.value
            if not isinstance(mode, SolverMode):
                raise TypeError("SET_SOLVER requires a SolverMode")
            if mode is not runtime.solver_mode:
                runtime = self._create_runtime(
                    mode,
                    generation=runtime.generation + 1,
                    paused=runtime.paused,
                    time_scale=runtime.time_scale,
                )
                self._publish(runtime)
        return runtime

    def _run(self) -> None:
        runtime = self._create_runtime(
            SolverMode.BARNES_HUT,
            generation=0,
            paused=False,
            time_scale=1.0,
        )
        self._publish(runtime)
        next_step_at = perf_counter()

        while not self._stop_event.is_set():
            timeout = 0.05
            if not runtime.paused:
                timeout = max(0.0, min(0.05, next_step_at - perf_counter()))
            try:
                command = self._commands.get(timeout=timeout)
            except queue.Empty:
                command = None

            while command is not None:
                updated = self._handle_command(runtime, command)
                if updated is None:
                    return
                runtime = updated
                try:
                    command = self._commands.get_nowait()
                except queue.Empty:
                    command = None
                next_step_at = perf_counter()

            if runtime.paused or self._stop_event.is_set():
                continue

            now = perf_counter()
            if now < next_step_at:
                continue
            self._advance_once(runtime)
            interval = runtime.galaxy.config.time_step / runtime.time_scale
            next_step_at += interval
            minimum_schedule = perf_counter() - MAX_SCHEDULE_LAG_STEPS * interval
            if next_step_at < minimum_schedule:
                next_step_at = minimum_schedule

        self._logger.info("Physics worker stopped normally")
