"""Deterministic, physically motivated initial conditions for Gravity's V1 galaxy."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np
import numpy.typing as npt

from gravity.core.state import FloatArray, ParticleState
from gravity.physics.potentials import PlummerPotential
from gravity.physics.validation import validate_softening, validate_time_step

DEFAULT_GALAXY_SEED = 2_026_080_3
MIN_PARTICLE_COUNT = 100
MAX_PARTICLE_COUNT = 50_000
MAX_SEED = 2**32 - 1
MIN_DISK_OUTER_RADIUS = 6.0
MAX_DISK_OUTER_RADIUS = 24.0
MIN_GALAXY_SOFTENING = 0.02
MAX_GALAXY_SOFTENING = 0.25
MIN_GALAXY_TIME_STEP = 0.0025
MAX_GALAXY_TIME_STEP = 0.08

type ComponentArray = npt.NDArray[np.uint8]


class GalaxyComponent(IntEnum):
    """Stable component labels stored beside, never inside, physics state."""

    DISK = 0
    BULGE = 1
    CENTRAL = 2


def _real_number(value: float, name: str) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError) as error:
        raise TypeError(f"{name} must be a real number") from error
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    return converted


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    converted = _real_number(value, name)
    valid = converted >= 0.0 if allow_zero else converted > 0.0
    if not valid:
        qualifier = "non-negative" if allow_zero else "strictly positive"
        raise ValueError(f"{name} must be {qualifier}")
    return converted


def _integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    return int(value)


@dataclass(frozen=True, slots=True)
class GalaxyConfig:
    """Complete reproducible configuration for the V1 spiral galaxy."""

    particle_count: int = 10_000
    seed: int = DEFAULT_GALAXY_SEED
    disk_mass: float = 0.60
    bulge_mass: float = 0.20
    central_mass: float = 0.02
    halo_mass: float = 1.20
    disk_scale_length: float = 2.05
    disk_outer_radius: float = 10.8
    disk_scale_height: float = 0.12
    bulge_scale_radius: float = 0.55
    bulge_outer_radius: float = 4.2
    halo_scale_radius: float = 6.0
    bulge_particle_fraction: float = 0.16
    arm_count: int = 4
    spiral_fraction: float = 0.82
    spiral_winding: float = 0.78
    spiral_scatter: float = 0.22
    disk_velocity_dispersion: float = 0.035
    vertical_velocity_dispersion: float = 0.020
    bulge_velocity_scale: float = 0.70
    softening: float = 0.08
    time_step: float = 0.02

    def __post_init__(self) -> None:
        particle_count = _integer(self.particle_count, "particle_count")
        if not MIN_PARTICLE_COUNT <= particle_count <= MAX_PARTICLE_COUNT:
            raise ValueError(
                f"particle_count must be between {MIN_PARTICLE_COUNT} and {MAX_PARTICLE_COUNT}"
            )
        seed = _integer(self.seed, "seed")
        if not 0 <= seed <= MAX_SEED:
            raise ValueError("seed must be an unsigned 32-bit integer")

        object.__setattr__(self, "particle_count", particle_count)
        object.__setattr__(self, "seed", seed)
        for name in ("disk_mass", "bulge_mass"):
            object.__setattr__(self, name, _positive(getattr(self, name), name))
        for name in ("central_mass", "halo_mass"):
            object.__setattr__(self, name, _positive(getattr(self, name), name, allow_zero=True))
        for name in (
            "disk_scale_length",
            "disk_outer_radius",
            "disk_scale_height",
            "bulge_scale_radius",
            "bulge_outer_radius",
            "halo_scale_radius",
        ):
            object.__setattr__(self, name, _positive(getattr(self, name), name))

        if self.disk_outer_radius < 3.0 * self.disk_scale_length:
            raise ValueError("disk_outer_radius must be at least three disk scale lengths")
        if not MIN_DISK_OUTER_RADIUS <= self.disk_outer_radius <= MAX_DISK_OUTER_RADIUS:
            raise ValueError(
                f"disk_outer_radius must be between {MIN_DISK_OUTER_RADIUS} "
                f"and {MAX_DISK_OUTER_RADIUS}"
            )
        if self.bulge_outer_radius <= self.bulge_scale_radius:
            raise ValueError("bulge_outer_radius must exceed bulge_scale_radius")

        bulge_fraction = _real_number(self.bulge_particle_fraction, "bulge_particle_fraction")
        if not 0.0 < bulge_fraction < 1.0:
            raise ValueError("bulge_particle_fraction must lie strictly between zero and one")
        object.__setattr__(self, "bulge_particle_fraction", bulge_fraction)

        arm_count = _integer(self.arm_count, "arm_count")
        if not 1 <= arm_count <= 8:
            raise ValueError("arm_count must be between one and eight")
        object.__setattr__(self, "arm_count", arm_count)

        spiral_fraction = _real_number(self.spiral_fraction, "spiral_fraction")
        if not 0.0 <= spiral_fraction <= 1.0:
            raise ValueError("spiral_fraction must lie between zero and one")
        object.__setattr__(self, "spiral_fraction", spiral_fraction)
        object.__setattr__(
            self, "spiral_winding", _real_number(self.spiral_winding, "spiral_winding")
        )
        object.__setattr__(
            self,
            "spiral_scatter",
            _positive(self.spiral_scatter, "spiral_scatter", allow_zero=True),
        )

        for name in (
            "disk_velocity_dispersion",
            "vertical_velocity_dispersion",
            "bulge_velocity_scale",
        ):
            value = _positive(getattr(self, name), name, allow_zero=True)
            if value > 1.0:
                raise ValueError(f"{name} cannot exceed one")
            object.__setattr__(self, name, value)

        softening = validate_softening(self.softening)
        if not MIN_GALAXY_SOFTENING <= softening <= MAX_GALAXY_SOFTENING:
            raise ValueError(
                f"softening must be between {MIN_GALAXY_SOFTENING} "
                f"and {MAX_GALAXY_SOFTENING} for the V1 galaxy"
            )
        time_step = validate_time_step(self.time_step)
        if not MIN_GALAXY_TIME_STEP <= time_step <= MAX_GALAXY_TIME_STEP:
            raise ValueError(
                f"time_step must be between {MIN_GALAXY_TIME_STEP} "
                f"and {MAX_GALAXY_TIME_STEP} for the V1 galaxy"
            )
        object.__setattr__(self, "softening", softening)
        object.__setattr__(self, "time_step", time_step)
        if self.disk_particle_count < 1 or self.bulge_particle_count < 1:
            raise ValueError("configuration must allocate at least one disk and bulge particle")

    @property
    def central_particle_count(self) -> int:
        return int(self.central_mass > 0.0)

    @property
    def noncentral_particle_count(self) -> int:
        return self.particle_count - self.central_particle_count

    @property
    def bulge_particle_count(self) -> int:
        return max(1, int(round(self.noncentral_particle_count * self.bulge_particle_fraction)))

    @property
    def disk_particle_count(self) -> int:
        return self.noncentral_particle_count - self.bulge_particle_count

    @property
    def live_mass(self) -> float:
        return self.disk_mass + self.bulge_mass + self.central_mass


def _validate_radii(radius: npt.ArrayLike) -> FloatArray:
    radii = np.asarray(radius, dtype=np.float64)
    if not np.all(np.isfinite(radii)) or np.any(radii < 0.0):
        raise ValueError("radius must contain only finite non-negative values")
    return np.ascontiguousarray(radii, dtype=np.float64)


@dataclass(frozen=True, slots=True)
class GalaxyMassModel:
    """Smooth mass curve used only to construct initial orbital velocities."""

    config: GalaxyConfig
    halo: PlummerPotential = field(init=False)
    _disk_normalization: float = field(init=False, repr=False)
    _bulge_normalization: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "halo",
            PlummerPotential(self.config.halo_mass, self.config.halo_scale_radius),
        )
        disk_limit = self.config.disk_outer_radius / self.config.disk_scale_length
        disk_normalization = 1.0 - math.exp(-disk_limit) * (1.0 + disk_limit)
        bulge_limit = self.config.bulge_outer_radius
        bulge_normalization = (bulge_limit / (bulge_limit + self.config.bulge_scale_radius)) ** 2
        object.__setattr__(self, "_disk_normalization", disk_normalization)
        object.__setattr__(self, "_bulge_normalization", bulge_normalization)

    def disk_enclosed_mass(self, radius: npt.ArrayLike) -> FloatArray:
        radii = _validate_radii(radius)
        limited = np.minimum(radii, self.config.disk_outer_radius)
        scaled = limited / self.config.disk_scale_length
        fraction = (1.0 - np.exp(-scaled) * (1.0 + scaled)) / self._disk_normalization
        return np.ascontiguousarray(self.config.disk_mass * fraction)

    def bulge_enclosed_mass(self, radius: npt.ArrayLike) -> FloatArray:
        radii = _validate_radii(radius)
        limited = np.minimum(radii, self.config.bulge_outer_radius)
        fraction = (limited / (limited + self.config.bulge_scale_radius)) ** 2
        return np.ascontiguousarray(self.config.bulge_mass * fraction / self._bulge_normalization)

    def central_enclosed_mass(self, radius: npt.ArrayLike) -> FloatArray:
        radii = _validate_radii(radius)
        squared_radius = radii * radii
        denominator = (squared_radius + self.config.softening**2) ** 1.5
        enclosed = self.config.central_mass * radii * squared_radius / denominator
        return np.ascontiguousarray(enclosed)

    def total_enclosed_mass(self, radius: npt.ArrayLike) -> FloatArray:
        radii = _validate_radii(radius)
        total = self.disk_enclosed_mass(radii)
        total += self.bulge_enclosed_mass(radii)
        total += self.central_enclosed_mass(radii)
        total += self.halo.enclosed_mass(radii)
        return np.ascontiguousarray(total)

    def radial_acceleration(self, radius: npt.ArrayLike) -> FloatArray:
        radii = _validate_radii(radius)
        result = np.zeros_like(radii)
        nonzero = radii > 0.0
        enclosed = self.total_enclosed_mass(radii)
        result[nonzero] = -enclosed[nonzero] / (radii[nonzero] * radii[nonzero])
        return np.ascontiguousarray(result)

    def circular_speed(self, radius: npt.ArrayLike) -> FloatArray:
        radii = _validate_radii(radius)
        acceleration = self.radial_acceleration(radii)
        return np.ascontiguousarray(np.sqrt(np.maximum(0.0, -radii * acceleration)))


@dataclass(frozen=True, slots=True)
class GalaxyInitialConditions:
    """Mutable physics state plus immutable scenario identity and component labels."""

    state: ParticleState
    components: ComponentArray
    config: GalaxyConfig
    mass_model: GalaxyMassModel
    name: str = "Galaxie spirale"

    def __post_init__(self) -> None:
        components = self.components
        if not isinstance(components, np.ndarray) or components.dtype != np.uint8:
            raise TypeError("components must be a uint8 NumPy array")
        if components.shape != (self.state.particle_count,):
            raise ValueError(f"components must have shape ({self.state.particle_count},)")
        if not components.flags.c_contiguous:
            raise ValueError("components must be C-contiguous")
        allowed = np.array([component.value for component in GalaxyComponent], dtype=np.uint8)
        if not np.all(np.isin(components, allowed)):
            raise ValueError("components contain an unknown galaxy component")
        if self.state.particle_count != self.config.particle_count:
            raise ValueError("state and configuration particle counts differ")
        expected_counts = {
            GalaxyComponent.DISK: self.config.disk_particle_count,
            GalaxyComponent.BULGE: self.config.bulge_particle_count,
            GalaxyComponent.CENTRAL: self.config.central_particle_count,
        }
        for component, expected in expected_counts.items():
            if int(np.count_nonzero(components == component.value)) != expected:
                raise ValueError(f"component count differs for {component.name.lower()}")
        if self.mass_model.config != self.config:
            raise ValueError("mass model and scenario configurations differ")
        components.setflags(write=False)


def _sample_exponential_disk_radii(
    rng: np.random.Generator,
    count: int,
    scale_length: float,
    outer_radius: float,
) -> FloatArray:
    """Invert the truncated two-dimensional exponential-disk CDF by bisection."""

    limit = outer_radius / scale_length
    cdf_limit = 1.0 - math.exp(-limit) * (1.0 + limit)
    targets = rng.random(count) * cdf_limit
    lower = np.zeros(count, dtype=np.float64)
    upper = np.full(count, limit, dtype=np.float64)
    for _ in range(54):
        middle = 0.5 * (lower + upper)
        cdf = 1.0 - np.exp(-middle) * (1.0 + middle)
        below_target = cdf < targets
        lower[below_target] = middle[below_target]
        upper[~below_target] = middle[~below_target]
    return np.ascontiguousarray(0.5 * (lower + upper) * scale_length)


def _sample_disk_positions(rng: np.random.Generator, config: GalaxyConfig) -> FloatArray:
    count = config.disk_particle_count
    radius = _sample_exponential_disk_radii(
        rng,
        count,
        config.disk_scale_length,
        config.disk_outer_radius,
    )
    angle = rng.uniform(0.0, 2.0 * math.pi, count)
    if config.spiral_fraction > 0.0:
        in_arm = rng.random(count) < config.spiral_fraction
        arm = rng.integers(0, config.arm_count, count)
        arm_angle = (
            arm * (2.0 * math.pi / config.arm_count)
            + radius * config.spiral_winding
            + rng.normal(0.0, config.spiral_scatter, count)
        )
        angle[in_arm] = arm_angle[in_arm]

    positions = np.empty((count, 3), dtype=np.float64)
    positions[:, 0] = radius * np.cos(angle)
    positions[:, 1] = rng.normal(0.0, config.disk_scale_height, count)
    positions[:, 2] = radius * np.sin(angle)
    return positions


def _sample_bulge_positions(rng: np.random.Generator, config: GalaxyConfig) -> FloatArray:
    count = config.bulge_particle_count
    cdf_limit = (
        config.bulge_outer_radius / (config.bulge_outer_radius + config.bulge_scale_radius)
    ) ** 2
    root_cdf = np.sqrt(rng.random(count) * cdf_limit)
    radius = config.bulge_scale_radius * root_cdf / (1.0 - root_cdf)
    polar_cosine = rng.uniform(-1.0, 1.0, count)
    azimuth = rng.uniform(0.0, 2.0 * math.pi, count)
    planar_scale = radius * np.sqrt(1.0 - polar_cosine * polar_cosine)

    positions = np.empty((count, 3), dtype=np.float64)
    positions[:, 0] = planar_scale * np.cos(azimuth)
    positions[:, 1] = radius * polar_cosine
    positions[:, 2] = planar_scale * np.sin(azimuth)
    return positions


def _build_masses_and_components(config: GalaxyConfig) -> tuple[FloatArray, ComponentArray]:
    disk_count = config.disk_particle_count
    bulge_count = config.bulge_particle_count
    masses = np.empty(config.particle_count, dtype=np.float64)
    components = np.empty(config.particle_count, dtype=np.uint8)
    masses[:disk_count] = config.disk_mass / disk_count
    components[:disk_count] = GalaxyComponent.DISK
    bulge_end = disk_count + bulge_count
    masses[disk_count:bulge_end] = config.bulge_mass / bulge_count
    components[disk_count:bulge_end] = GalaxyComponent.BULGE
    if config.central_particle_count:
        masses[bulge_end] = config.central_mass
        components[bulge_end] = GalaxyComponent.CENTRAL
    return masses, components


def _center_noncentral_positions(positions: FloatArray, masses: FloatArray, count: int) -> None:
    live_mass = float(np.sum(masses[:count]))
    offset = np.sum(positions[:count] * masses[:count, None], axis=0) / live_mass
    positions[:count] -= offset


def _sample_velocities(
    rng: np.random.Generator,
    positions: FloatArray,
    masses: FloatArray,
    config: GalaxyConfig,
    mass_model: GalaxyMassModel,
) -> FloatArray:
    velocities = np.zeros_like(positions)
    disk_count = config.disk_particle_count
    noncentral_count = config.noncentral_particle_count

    disk_positions = positions[:disk_count]
    radius = np.hypot(disk_positions[:, 0], disk_positions[:, 2])
    safe_radius = np.maximum(radius, np.finfo(np.float64).eps)
    radial_unit = np.zeros_like(disk_positions)
    radial_unit[:, 0] = disk_positions[:, 0] / safe_radius
    radial_unit[:, 2] = disk_positions[:, 2] / safe_radius
    tangential_unit = np.zeros_like(disk_positions)
    tangential_unit[:, 0] = -radial_unit[:, 2]
    tangential_unit[:, 2] = radial_unit[:, 0]

    circular_speed = mass_model.circular_speed(radius)
    tangential_multiplier = 1.0 + rng.normal(
        0.0,
        config.disk_velocity_dispersion,
        disk_count,
    )
    tangential_multiplier = np.maximum(tangential_multiplier, 0.10)
    radial_speed = rng.normal(0.0, config.disk_velocity_dispersion * circular_speed)
    vertical_speed = rng.normal(0.0, config.vertical_velocity_dispersion * circular_speed)
    velocities[:disk_count] = (
        tangential_unit * (circular_speed * tangential_multiplier)[:, None]
        + radial_unit * radial_speed[:, None]
    )
    velocities[:disk_count, 1] = vertical_speed

    bulge_positions = positions[disk_count:noncentral_count]
    bulge_radius = np.linalg.norm(bulge_positions, axis=1)
    bulge_circular_speed = mass_model.circular_speed(bulge_radius)
    bulge_sigma = config.bulge_velocity_scale * bulge_circular_speed / math.sqrt(3.0)
    velocities[disk_count:noncentral_count] = (
        rng.normal(
            0.0,
            1.0,
            bulge_positions.shape,
        )
        * bulge_sigma[:, None]
    )

    noncentral_mass = float(np.sum(masses[:noncentral_count]))
    bulk_velocity = (
        np.sum(velocities[:noncentral_count] * masses[:noncentral_count, None], axis=0)
        / noncentral_mass
    )
    velocities[:noncentral_count] -= bulk_velocity
    return velocities


def generate_spiral_galaxy(config: GalaxyConfig | None = None) -> GalaxyInitialConditions:
    """Generate one reproducible disk/bulge/central state and its analytic halo."""

    selected = GalaxyConfig() if config is None else config
    if not isinstance(selected, GalaxyConfig):
        raise TypeError("config must be a GalaxyConfig")
    rng = np.random.default_rng(selected.seed)
    disk_positions = _sample_disk_positions(rng, selected)
    bulge_positions = _sample_bulge_positions(rng, selected)

    positions = np.zeros((selected.particle_count, 3), dtype=np.float64)
    disk_end = selected.disk_particle_count
    noncentral_end = selected.noncentral_particle_count
    positions[:disk_end] = disk_positions
    positions[disk_end:noncentral_end] = bulge_positions
    masses, components = _build_masses_and_components(selected)
    _center_noncentral_positions(positions, masses, noncentral_end)

    mass_model = GalaxyMassModel(selected)
    velocities = _sample_velocities(rng, positions, masses, selected, mass_model)
    order = rng.permutation(selected.particle_count)
    state = ParticleState.from_arrays(
        positions[order],
        velocities[order],
        masses[order],
    )
    ordered_components = np.ascontiguousarray(components[order], dtype=np.uint8)
    return GalaxyInitialConditions(
        state=state,
        components=ordered_components,
        config=selected,
        mass_model=mass_model,
    )
