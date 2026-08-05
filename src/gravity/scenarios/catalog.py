"""Catalogue of deterministic initial conditions for the interactive laboratory."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from gravity.core.experiment import ExperimentConfig, ScenarioKind
from gravity.core.state import FloatArray, ParticleState
from gravity.physics.composite import AdditiveAccelerationField
from gravity.physics.potentials import PlummerPotential
from gravity.scenarios.galaxy import (
    GalaxyComponent,
    GalaxyConfig,
    generate_spiral_galaxy,
)

DEFAULT_SOFTENING = 0.08
DEFAULT_TIME_STEP = 0.02
DEFAULT_LIVE_MASS = 0.82
DISK_RADIUS = 7.5
RING_RADIUS = 5.2
SPHERE_RADIUS = 5.5
RANDOM_EXTENT = 5.5

type ComponentArray = npt.NDArray[np.uint8]
type OriginArray = npt.NDArray[np.uint8]


@dataclass(frozen=True, slots=True)
class GeneratedScenario:
    """Complete physics inputs produced from one reproducible experiment."""

    state: ParticleState
    components: ComponentArray
    origins: OriginArray
    experiment: ExperimentConfig
    external_fields: tuple[AdditiveAccelerationField, ...] = ()
    time_step: float = DEFAULT_TIME_STEP
    softening: float = DEFAULT_SOFTENING

    def __post_init__(self) -> None:
        if self.state.particle_count != self.experiment.particle_count:
            raise ValueError("state and experiment particle counts differ")
        for name, labels in (("components", self.components), ("origins", self.origins)):
            if not isinstance(labels, np.ndarray) or labels.dtype != np.uint8:
                raise TypeError(f"{name} must be a uint8 NumPy array")
            if labels.shape != (self.state.particle_count,):
                raise ValueError(f"{name} must have shape ({self.state.particle_count},)")
            if not labels.flags.c_contiguous:
                raise ValueError(f"{name} must be C-contiguous")
            labels.setflags(write=False)
        if not math.isfinite(self.time_step) or self.time_step <= 0.0:
            raise ValueError("time_step must be finite and positive")
        if not math.isfinite(self.softening) or self.softening < 0.0:
            raise ValueError("softening must be finite and non-negative")

    @property
    def name(self) -> str:
        return self.experiment.scenario.french_name


def _equal_masses(count: int, total_mass: float = DEFAULT_LIVE_MASS) -> FloatArray:
    return np.full(count, total_mass / count, dtype=np.float64)


def _generic_components(count: int) -> ComponentArray:
    return np.full(count, GalaxyComponent.DISK.value, dtype=np.uint8)


def _single_origin(count: int) -> OriginArray:
    return np.zeros(count, dtype=np.uint8)


def _remove_bulk_motion(
    positions: FloatArray,
    velocities: FloatArray,
    masses: FloatArray,
) -> None:
    total_mass = float(np.sum(masses))
    positions -= np.sum(positions * masses[:, None], axis=0) / total_mass
    velocities -= np.sum(velocities * masses[:, None], axis=0) / total_mass


def _assemble_generic(
    experiment: ExperimentConfig,
    positions: FloatArray,
    velocities: FloatArray,
    *,
    masses: FloatArray | None = None,
    components: ComponentArray | None = None,
    origins: OriginArray | None = None,
    external_fields: tuple[AdditiveAccelerationField, ...] = (),
) -> GeneratedScenario:
    selected_masses = _equal_masses(experiment.particle_count) if masses is None else masses
    _remove_bulk_motion(positions, velocities, selected_masses)
    state = ParticleState.from_arrays(positions, velocities, selected_masses)
    selected_components = (
        _generic_components(experiment.particle_count) if components is None else components
    )
    selected_origins = _single_origin(experiment.particle_count) if origins is None else origins
    return GeneratedScenario(
        state=state,
        components=np.ascontiguousarray(selected_components, dtype=np.uint8),
        origins=np.ascontiguousarray(selected_origins, dtype=np.uint8),
        experiment=experiment,
        external_fields=external_fields,
    )


def _uniform_angles(rng: np.random.Generator, count: int) -> FloatArray:
    return np.ascontiguousarray(rng.uniform(0.0, 2.0 * math.pi, count))


def _disk_positions(
    rng: np.random.Generator,
    count: int,
    radius: FloatArray,
    height: float,
) -> FloatArray:
    angle = _uniform_angles(rng, count)
    positions = np.empty((count, 3), dtype=np.float64)
    positions[:, 0] = radius * np.cos(angle)
    positions[:, 1] = rng.normal(0.0, height, count)
    positions[:, 2] = radius * np.sin(angle)
    return positions


def _circular_velocities(
    rng: np.random.Generator,
    positions: FloatArray,
    live_enclosed_mass: FloatArray,
    halo: PlummerPotential,
) -> FloatArray:
    radius = np.hypot(positions[:, 0], positions[:, 2])
    safe_radius = np.maximum(radius, np.finfo(np.float64).eps)
    enclosed = live_enclosed_mass + halo.enclosed_mass(radius)
    speed = np.sqrt(np.maximum(0.0, enclosed / safe_radius))
    speed *= np.maximum(0.2, 1.0 + rng.normal(0.0, 0.025, radius.size))
    velocities = np.zeros_like(positions)
    velocities[:, 0] = -positions[:, 2] / safe_radius * speed
    velocities[:, 2] = positions[:, 0] / safe_radius * speed
    velocities[:, 1] = rng.normal(0.0, 0.012 * np.maximum(speed, 0.05))
    return velocities


def _generate_uniform_disk(experiment: ExperimentConfig) -> GeneratedScenario:
    rng = np.random.default_rng(experiment.seed)
    radius = DISK_RADIUS * np.sqrt(rng.random(experiment.particle_count))
    positions = _disk_positions(rng, experiment.particle_count, radius, 0.09)
    halo = PlummerPotential(0.80, 5.5)
    live_enclosed = DEFAULT_LIVE_MASS * np.square(radius / DISK_RADIUS)
    velocities = _circular_velocities(rng, positions, live_enclosed, halo)
    return _assemble_generic(experiment, positions, velocities, external_fields=(halo,))


def _generate_ring(experiment: ExperimentConfig) -> GeneratedScenario:
    rng = np.random.default_rng(experiment.seed)
    radius = np.clip(
        rng.normal(RING_RADIUS, 0.42, experiment.particle_count),
        RING_RADIUS - 1.25,
        RING_RADIUS + 1.25,
    )
    positions = _disk_positions(rng, experiment.particle_count, radius, 0.065)
    halo = PlummerPotential(1.05, 4.5)
    order = np.argsort(radius)
    enclosed = np.empty(experiment.particle_count, dtype=np.float64)
    enclosed[order] = (
        DEFAULT_LIVE_MASS
        * (np.arange(experiment.particle_count) + 0.5)
        / (experiment.particle_count)
    )
    velocities = _circular_velocities(rng, positions, enclosed, halo)
    return _assemble_generic(experiment, positions, velocities, external_fields=(halo,))


def _uniform_sphere_positions(
    rng: np.random.Generator,
    count: int,
    radius: float,
) -> FloatArray:
    directions = rng.normal(0.0, 1.0, (count, 3))
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    radial = radius * np.cbrt(rng.random(count))
    return np.ascontiguousarray(directions * radial[:, None])


def _virial_random_velocities(
    rng: np.random.Generator,
    count: int,
    radius: float,
    *,
    scale: float = 1.0,
) -> FloatArray:
    sigma = scale * math.sqrt(DEFAULT_LIVE_MASS / (5.0 * radius))
    return np.ascontiguousarray(rng.normal(0.0, sigma, (count, 3)))


def _generate_sphere(experiment: ExperimentConfig) -> GeneratedScenario:
    rng = np.random.default_rng(experiment.seed)
    positions = _uniform_sphere_positions(rng, experiment.particle_count, SPHERE_RADIUS)
    velocities = _virial_random_velocities(
        rng,
        experiment.particle_count,
        SPHERE_RADIUS,
    )
    return _assemble_generic(experiment, positions, velocities)


def _generate_random_cloud(
    experiment: ExperimentConfig,
    *,
    chaotic: bool,
) -> GeneratedScenario:
    rng = np.random.default_rng(experiment.seed)
    positions = np.ascontiguousarray(
        rng.uniform(-RANDOM_EXTENT, RANDOM_EXTENT, (experiment.particle_count, 3))
    )
    if chaotic:
        escape_scale = math.sqrt(2.0 * DEFAULT_LIVE_MASS / RANDOM_EXTENT)
        velocities = np.ascontiguousarray(
            rng.uniform(-1.25 * escape_scale, 1.25 * escape_scale, positions.shape)
        )
    else:
        velocities = _virial_random_velocities(
            rng,
            experiment.particle_count,
            RANDOM_EXTENT,
            scale=0.80,
        )
    return _assemble_generic(experiment, positions, velocities)


def _small_galaxy_config(
    experiment: ExperimentConfig,
    count: int,
    seed: int,
) -> GalaxyConfig:
    return GalaxyConfig(
        particle_count=count,
        seed=seed,
        disk_mass=experiment.disk_mass / 2.0,
        bulge_mass=experiment.bulge_mass / 2.0,
        central_mass=experiment.central_mass / 2.0,
        halo_mass=0.0,
        disk_scale_length=1.30,
        disk_outer_radius=6.0,
        disk_scale_height=0.08,
        bulge_scale_radius=0.32,
        bulge_outer_radius=2.4,
        halo_scale_radius=3.5,
        disk_velocity_dispersion=0.025,
        vertical_velocity_dispersion=0.015,
        bulge_velocity_scale=0.58,
    )


def _rotate_x(values: FloatArray, angle: float) -> FloatArray:
    cosine = math.cos(angle)
    sine = math.sin(angle)
    rotated = values.copy()
    rotated[:, 1] = cosine * values[:, 1] - sine * values[:, 2]
    rotated[:, 2] = sine * values[:, 1] + cosine * values[:, 2]
    return rotated


def _generate_collision(
    experiment: ExperimentConfig,
    *,
    oblique: bool,
) -> GeneratedScenario:
    left_count = experiment.particle_count // 2
    right_count = experiment.particle_count - left_count
    left = generate_spiral_galaxy(_small_galaxy_config(experiment, left_count, experiment.seed))
    right_seed = (experiment.seed * 1_664_525 + 1_013_904_223) & 0x7FFF_FFFF
    right = generate_spiral_galaxy(_small_galaxy_config(experiment, right_count, right_seed))

    left_positions = left.state.positions.copy()
    right_positions = right.state.positions.copy()
    left_velocities = left.state.velocities.copy()
    right_velocities = right.state.velocities.copy()
    if oblique:
        left_positions = _rotate_x(left_positions, math.radians(-18.0))
        right_positions = _rotate_x(right_positions, math.radians(52.0))
        left_velocities = _rotate_x(left_velocities, math.radians(-18.0))
        right_velocities = _rotate_x(right_velocities, math.radians(52.0))
        left_positions += np.array([-6.7, 0.0, -2.2])
        right_positions += np.array([6.7, 0.0, 2.2])
        left_velocities += np.array([0.13, 0.0, 0.045])
        right_velocities += np.array([-0.13, 0.0, -0.045])
    else:
        left_positions += np.array([-7.0, 0.0, 0.0])
        right_positions += np.array([7.0, 0.0, 0.0])
        left_velocities += np.array([0.145, 0.0, 0.0])
        right_velocities += np.array([-0.145, 0.0, 0.0])

    positions = np.ascontiguousarray(np.vstack((left_positions, right_positions)))
    velocities = np.ascontiguousarray(np.vstack((left_velocities, right_velocities)))
    masses = np.ascontiguousarray(np.concatenate((left.state.masses, right.state.masses)))
    components = np.ascontiguousarray(np.concatenate((left.components, right.components)))
    origins = np.concatenate(
        (
            np.zeros(left_count, dtype=np.uint8),
            np.ones(right_count, dtype=np.uint8),
        )
    )
    rng = np.random.default_rng(experiment.seed ^ 0x4A17_3C29)
    order = rng.permutation(experiment.particle_count)
    return _assemble_generic(
        experiment,
        positions[order],
        velocities[order],
        masses=masses[order],
        components=components[order],
        origins=origins[order],
    )


def _generate_spiral(experiment: ExperimentConfig) -> GeneratedScenario:
    galaxy = generate_spiral_galaxy(
        GalaxyConfig(
            particle_count=experiment.particle_count,
            seed=experiment.seed,
            disk_mass=experiment.disk_mass,
            bulge_mass=experiment.bulge_mass,
            central_mass=experiment.central_mass,
        )
    )
    return GeneratedScenario(
        state=galaxy.state,
        components=galaxy.components,
        origins=_single_origin(experiment.particle_count),
        experiment=experiment,
        external_fields=(galaxy.mass_model.halo,),
        time_step=galaxy.config.time_step,
        softening=galaxy.config.softening,
    )


def generate_experiment(experiment: ExperimentConfig | None = None) -> GeneratedScenario:
    """Generate any catalogue entry from the same validated public contract."""

    selected = ExperimentConfig() if experiment is None else experiment
    if not isinstance(selected, ExperimentConfig):
        raise TypeError("experiment must be an ExperimentConfig")
    if selected.scenario is ScenarioKind.SPIRAL_GALAXY:
        return _generate_spiral(selected)
    if selected.scenario is ScenarioKind.UNIFORM_DISK:
        return _generate_uniform_disk(selected)
    if selected.scenario is ScenarioKind.RING:
        return _generate_ring(selected)
    if selected.scenario is ScenarioKind.SPHERE:
        return _generate_sphere(selected)
    if selected.scenario is ScenarioKind.HEAD_ON_COLLISION:
        return _generate_collision(selected, oblique=False)
    if selected.scenario is ScenarioKind.OBLIQUE_COLLISION:
        return _generate_collision(selected, oblique=True)
    if selected.scenario is ScenarioKind.RANDOM_BOUND:
        return _generate_random_cloud(selected, chaotic=False)
    if selected.scenario is ScenarioKind.TOTAL_CHAOS:
        return _generate_random_cloud(selected, chaotic=True)
    raise AssertionError(f"unhandled scenario: {selected.scenario}")
