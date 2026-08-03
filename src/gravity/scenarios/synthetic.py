"""Deterministic visual-only particle field for the step-3 graphics gate."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_PARTICLE_COUNT = 10_000
DEFAULT_SEED = 2_026_080_3
VERTEX_COMPONENTS = 7


@dataclass(frozen=True, slots=True)
class ParticleField:
    """One contiguous interleaved buffer: xyz, rgb, and apparent size."""

    vertices: np.ndarray

    def __post_init__(self) -> None:
        if self.vertices.dtype != np.float32:
            raise TypeError("Particle vertices must use float32")
        if self.vertices.ndim != 2 or self.vertices.shape[1] != VERTEX_COMPONENTS:
            raise ValueError("Particle vertices must have shape (N, 7)")
        if not self.vertices.flags.c_contiguous:
            raise ValueError("Particle vertices must be C-contiguous")
        if not np.all(np.isfinite(self.vertices)):
            raise ValueError("Particle vertices must be finite")

    @property
    def count(self) -> int:
        return int(self.vertices.shape[0])

    @property
    def byte_size(self) -> int:
        return int(self.vertices.nbytes)


def generate_synthetic_galaxy(
    count: int = DEFAULT_PARTICLE_COUNT,
    *,
    seed: int = DEFAULT_SEED,
) -> ParticleField:
    """Create a visually galactic cloud without claiming physical correctness."""

    if count < 1:
        raise ValueError("Particle count must be positive")

    rng = np.random.default_rng(seed)
    bulge_mask = rng.random(count) < 0.16
    radius = np.minimum(rng.gamma(shape=2.0, scale=2.05, size=count), 10.8)
    arm = rng.integers(0, 4, size=count)
    angle = arm * (np.pi / 2.0) + radius * 0.78 + rng.normal(0.0, 0.22, count)

    x = radius * np.cos(angle)
    z = radius * np.sin(angle)
    y = rng.normal(0.0, 0.10 + 0.018 * radius, count)

    bulge_count = int(np.count_nonzero(bulge_mask))
    if bulge_count:
        direction = rng.normal(0.0, 1.0, (bulge_count, 3))
        direction /= np.linalg.norm(direction, axis=1, keepdims=True)
        bulge_radius = np.minimum(rng.exponential(1.15, bulge_count), 4.2)
        bulge = direction * bulge_radius[:, None]
        x[bulge_mask] = bulge[:, 0]
        y[bulge_mask] = bulge[:, 1] * 0.72
        z[bulge_mask] = bulge[:, 2]
        radius[bulge_mask] = np.linalg.norm(bulge[:, [0, 2]], axis=1)

    radial_mix = np.clip(radius / 10.8, 0.0, 1.0)
    warm = np.array([1.0, 0.48, 0.20], dtype=np.float64)
    cool = np.array([0.28, 0.62, 1.0], dtype=np.float64)
    colors = warm[None, :] * (1.0 - radial_mix[:, None]) + cool[None, :] * radial_mix[:, None]
    colors += rng.normal(0.0, 0.045, colors.shape)
    colors = np.clip(colors, 0.08, 1.0)

    sizes = 1.15 + 2.7 * np.exp(-radius / 2.6) + rng.random(count) * 0.75
    sizes[bulge_mask] *= 1.18

    vertices = np.empty((count, VERTEX_COMPONENTS), dtype=np.float32)
    vertices[:, 0] = x
    vertices[:, 1] = y
    vertices[:, 2] = z
    vertices[:, 3:6] = colors
    vertices[:, 6] = sizes
    return ParticleField(np.ascontiguousarray(vertices))
