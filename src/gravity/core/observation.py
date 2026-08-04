"""Cheap, presentation-oriented diagnostics for interactive snapshots."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import numpy.typing as npt

from gravity.core.state import ParticleState
from gravity.physics.potentials import PlummerPotential

type Float32Array = npt.NDArray[np.float32]
type UInt8Array = npt.NDArray[np.uint8]
type BoolArray = npt.NDArray[np.bool_]


class ColorMode(StrEnum):
    """Physical quantity mapped to particle colour."""

    DISTANCE = "distance"
    SPEED = "speed"
    COMPONENT = "component"
    ENERGY = "energy"
    EJECTION = "ejection"

    @property
    def french_name(self) -> str:
        return {
            ColorMode.DISTANCE: "Distance au centre",
            ColorMode.SPEED: "Vitesse",
            ColorMode.COMPONENT: "Composant d'origine",
            ColorMode.ENERGY: "Énergie orbitale",
            ColorMode.EJECTION: "Liées / éjectées",
        }[self]


@dataclass(frozen=True, slots=True)
class ObservationStats:
    """Small immutable summary displayed by the UI."""

    center_of_mass: tuple[float, float, float]
    median_radius: float
    max_speed: float
    estimated_energy: float
    energy_drift_percent: float
    ejection_radius: float
    ejected_count: int

    def __post_init__(self) -> None:
        numeric = (
            *self.center_of_mass,
            self.median_radius,
            self.max_speed,
            self.estimated_energy,
            self.energy_drift_percent,
            self.ejection_radius,
        )
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("observation statistics must be finite")
        if self.median_radius < 0.0 or self.max_speed < 0.0 or self.ejection_radius <= 0.0:
            raise ValueError("observation distances and speeds must be non-negative")
        if self.ejected_count < 0:
            raise ValueError("ejected_count cannot be negative")


@dataclass(frozen=True, slots=True)
class ParticleObservations:
    """Read-only per-particle values used only for display and classification."""

    radii: Float32Array
    speeds: Float32Array
    specific_energies: Float32Array
    components: UInt8Array
    ejected: BoolArray
    stats: ObservationStats

    def __post_init__(self) -> None:
        count = int(self.radii.shape[0])
        arrays = (self.radii, self.speeds, self.specific_energies, self.components, self.ejected)
        if count < 1 or any(array.shape != (count,) for array in arrays):
            raise ValueError("observation arrays must share one non-empty shape")
        if self.radii.dtype != np.float32 or self.speeds.dtype != np.float32:
            raise TypeError("radii and speeds must use float32")
        if self.specific_energies.dtype != np.float32:
            raise TypeError("specific_energies must use float32")
        if self.components.dtype != np.uint8 or self.ejected.dtype != np.bool_:
            raise TypeError("components/ejected use uint8/bool")
        if not all(array.flags.c_contiguous for array in arrays):
            raise ValueError("observation arrays must be C-contiguous")
        if not all(np.all(np.isfinite(array)) for array in arrays[:3]):
            raise ValueError("observation values must be finite")
        if self.stats.ejected_count > count:
            raise ValueError("ejected_count cannot exceed the particle count")
        for array in arrays:
            array.setflags(write=False)


def initial_ejection_radius(state: ParticleState) -> float:
    """Derive a stable observation boundary from the initial 95th percentile."""

    center = np.sum(state.positions * state.masses[:, None], axis=0) / np.sum(state.masses)
    radii = np.linalg.norm(state.positions - center, axis=1)
    return max(12.0, 2.5 * float(np.percentile(radii, 95.0)))


def observe_particles(
    state: ParticleState,
    components: UInt8Array,
    external_fields: tuple[object, ...],
    *,
    softening: float,
    ejection_radius: float,
    reference_energy: float | None,
) -> ParticleObservations:
    """Estimate orbital state in O(N), without slowing Barnes-Hut with O(N²) work."""

    total_mass = float(np.sum(state.masses))
    center = np.sum(state.positions * state.masses[:, None], axis=0) / total_mass
    bulk_velocity = np.sum(state.velocities * state.masses[:, None], axis=0) / total_mass
    relative_positions = state.positions - center
    relative_velocities = state.velocities - bulk_velocity
    radii64 = np.linalg.norm(relative_positions, axis=1)
    speeds64 = np.linalg.norm(relative_velocities, axis=1)

    live_potential = -total_mass / np.sqrt(radii64 * radii64 + softening * softening)
    potential = live_potential
    absolute_radius_squared = np.einsum("ij,ij->i", state.positions, state.positions)
    for field in external_fields:
        if isinstance(field, PlummerPotential):
            potential = potential - field.mass / np.sqrt(
                absolute_radius_squared + field.scale_radius * field.scale_radius
            )
    specific_energy = 0.5 * speeds64 * speeds64 + potential
    radial_velocity = np.einsum("ij,ij->i", relative_positions, relative_velocities) / np.maximum(
        radii64, np.finfo(np.float64).eps
    )
    ejected = (radii64 > ejection_radius) & (radial_velocity > 0.0) & (specific_energy > 0.0)

    kinetic = 0.5 * float(np.dot(state.masses, speeds64 * speeds64))
    estimated_potential = 0.5 * float(np.dot(state.masses, live_potential))
    for field in external_fields:
        if isinstance(field, PlummerPotential):
            estimated_potential -= float(
                np.dot(
                    state.masses,
                    field.mass
                    / np.sqrt(absolute_radius_squared + field.scale_radius * field.scale_radius),
                )
            )
    estimated_energy = kinetic + estimated_potential
    baseline = estimated_energy if reference_energy is None else reference_energy
    drift = (
        0.0 if abs(baseline) < 1.0e-12 else 100.0 * (estimated_energy - baseline) / abs(baseline)
    )
    stats = ObservationStats(
        center_of_mass=(float(center[0]), float(center[1]), float(center[2])),
        median_radius=float(np.median(radii64)),
        max_speed=float(np.max(speeds64)),
        estimated_energy=estimated_energy,
        energy_drift_percent=drift,
        ejection_radius=ejection_radius,
        ejected_count=int(np.count_nonzero(ejected)),
    )
    return ParticleObservations(
        radii=np.ascontiguousarray(radii64, dtype=np.float32),
        speeds=np.ascontiguousarray(speeds64, dtype=np.float32),
        specific_energies=np.ascontiguousarray(specific_energy, dtype=np.float32),
        components=np.ascontiguousarray(components, dtype=np.uint8),
        ejected=np.ascontiguousarray(ejected, dtype=np.bool_),
        stats=stats,
    )
