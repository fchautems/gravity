from __future__ import annotations

import math
from dataclasses import dataclass

import pytest

from gravity.core.state import ParticleState


@dataclass(frozen=True, slots=True)
class CircularBinary:
    state: ParticleState
    softening: float
    angular_frequency: float
    period: float


@pytest.fixture
def circular_binary() -> CircularBinary:
    mass_first = 0.4
    mass_second = 0.6
    total_mass = mass_first + mass_second
    separation = 1.0
    softening = 0.02
    softened_distance_cubed = (separation * separation + softening * softening) ** 1.5
    angular_frequency = math.sqrt(total_mass / softened_distance_cubed)
    first_radius = separation * mass_second / total_mass
    second_radius = separation * mass_first / total_mass
    state = ParticleState.from_arrays(
        positions=[[-first_radius, 0.0, 0.0], [second_radius, 0.0, 0.0]],
        velocities=[
            [0.0, -angular_frequency * first_radius, 0.0],
            [0.0, angular_frequency * second_radius, 0.0],
        ],
        masses=[mass_first, mass_second],
    )
    return CircularBinary(
        state=state,
        softening=softening,
        angular_frequency=angular_frequency,
        period=2.0 * math.pi / angular_frequency,
    )
