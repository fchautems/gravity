"""Reproducible user-facing experiment configuration."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

DEFAULT_EXPERIMENT_SEED = 2_026_080_3
DEFAULT_DISK_MASS = 0.60
DEFAULT_BULGE_MASS = 0.20
DEFAULT_CENTRAL_MASS = 0.02
MIN_PARTICLE_COUNT = 100
MAX_PARTICLE_COUNT = 50_000
MAX_EXPERIMENT_SEED = 2**31 - 1
DUAL_SCENARIO_MIN_PARTICLES = 200
MIN_EXTENDED_MASS = 0.01
MAX_EXTENDED_MASS = 5.0
MAX_CENTRAL_MASS = 2.0


class ScenarioKind(StrEnum):
    """Stable identifiers for the initial-condition catalogue."""

    SPIRAL_GALAXY = "spiral-galaxy"
    UNIFORM_DISK = "uniform-disk"
    RING = "ring"
    SPHERE = "sphere"
    HEAD_ON_COLLISION = "head-on-collision"
    OBLIQUE_COLLISION = "oblique-collision"
    RANDOM_BOUND = "random-bound"
    TOTAL_CHAOS = "total-chaos"

    @property
    def french_name(self) -> str:
        return {
            ScenarioKind.SPIRAL_GALAXY: "Galaxie spirale",
            ScenarioKind.UNIFORM_DISK: "Disque uniforme",
            ScenarioKind.RING: "Anneau",
            ScenarioKind.SPHERE: "Sphère gravitationnelle",
            ScenarioKind.HEAD_ON_COLLISION: "Collision frontale",
            ScenarioKind.OBLIQUE_COLLISION: "Collision oblique",
            ScenarioKind.RANDOM_BOUND: "Aléatoire lié",
            ScenarioKind.TOTAL_CHAOS: "Chaos total",
        }[self]

    @property
    def french_description(self) -> str:
        return {
            ScenarioKind.SPIRAL_GALAXY: "Disque à quatre bras, bulbe, noyau et halo stable.",
            ScenarioKind.UNIFORM_DISK: "Disque plat sans bras, en rotation autour de son centre.",
            ScenarioKind.RING: "Couronne mince en rotation, volontairement sensible aux instabilités.",
            ScenarioKind.SPHERE: "Amas sphérique proche de l'équilibre gravitationnel.",
            ScenarioKind.HEAD_ON_COLLISION: "Deux petites galaxies lancées l'une vers l'autre.",
            ScenarioKind.OBLIQUE_COLLISION: "Deux galaxies inclinées avec un impact décentré.",
            ScenarioKind.RANDOM_BOUND: "Nuage désordonné mais assez lent pour rester globalement lié.",
            ScenarioKind.TOTAL_CHAOS: "Positions et vitesses désordonnées, sans garantie de rester lié.",
        }[self]

    @property
    def minimum_particles(self) -> int:
        if self in (ScenarioKind.HEAD_ON_COLLISION, ScenarioKind.OBLIQUE_COLLISION):
            return DUAL_SCENARIO_MIN_PARTICLES
        return MIN_PARTICLE_COUNT


SCENARIO_CATALOG = tuple(ScenarioKind)


def _integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _mass(value: float, name: str, *, allow_zero: bool = False, maximum: float) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError) as error:
        raise TypeError(f"{name} must be a real number") from error
    minimum = 0.0 if allow_zero else MIN_EXTENDED_MASS
    if not math.isfinite(converted) or not minimum <= converted <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return converted


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """Everything needed to reproduce one initial condition exactly."""

    scenario: ScenarioKind = ScenarioKind.SPIRAL_GALAXY
    particle_count: int = 10_000
    seed: int = DEFAULT_EXPERIMENT_SEED
    disk_mass: float = DEFAULT_DISK_MASS
    bulge_mass: float = DEFAULT_BULGE_MASS
    central_mass: float = DEFAULT_CENTRAL_MASS

    def __post_init__(self) -> None:
        if not isinstance(self.scenario, ScenarioKind):
            raise TypeError("scenario must be a ScenarioKind")
        particle_count = _integer(self.particle_count, "particle_count")
        if not MIN_PARTICLE_COUNT <= particle_count <= MAX_PARTICLE_COUNT:
            raise ValueError(
                f"particle_count must be between {MIN_PARTICLE_COUNT} and {MAX_PARTICLE_COUNT}"
            )
        if particle_count < self.scenario.minimum_particles:
            raise ValueError(
                f"{self.scenario.value} requires at least {self.scenario.minimum_particles} particles"
            )
        seed = _integer(self.seed, "seed")
        if not 0 <= seed <= MAX_EXPERIMENT_SEED:
            raise ValueError(f"seed must be between 0 and {MAX_EXPERIMENT_SEED}")
        object.__setattr__(
            self,
            "disk_mass",
            _mass(self.disk_mass, "disk_mass", maximum=MAX_EXTENDED_MASS),
        )
        object.__setattr__(
            self,
            "bulge_mass",
            _mass(self.bulge_mass, "bulge_mass", maximum=MAX_EXTENDED_MASS),
        )
        object.__setattr__(
            self,
            "central_mass",
            _mass(
                self.central_mass,
                "central_mass",
                allow_zero=True,
                maximum=MAX_CENTRAL_MASS,
            ),
        )

    @property
    def uses_galaxy_components(self) -> bool:
        """Whether the selected initial condition is built from the galaxy model."""

        return self.scenario in (
            ScenarioKind.SPIRAL_GALAXY,
            ScenarioKind.HEAD_ON_COLLISION,
            ScenarioKind.OBLIQUE_COLLISION,
        )


def estimated_barnes_hut_load(particle_count: int) -> float:
    """Return an indicative N log N load relative to the 10,000-body default."""

    validated = _integer(particle_count, "particle_count")
    if not MIN_PARTICLE_COUNT <= validated <= MAX_PARTICLE_COUNT:
        raise ValueError(
            f"particle_count must be between {MIN_PARTICLE_COUNT} and {MAX_PARTICLE_COUNT}"
        )
    baseline = 10_000 * math.log2(10_000)
    return validated * math.log2(validated) / baseline
