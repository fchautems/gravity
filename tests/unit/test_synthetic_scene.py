from __future__ import annotations

import numpy as np
import pytest

from gravity.scenarios.synthetic import ParticleField, generate_synthetic_galaxy


def test_synthetic_field_is_reproducible_and_gpu_ready() -> None:
    first = generate_synthetic_galaxy(10_000, seed=1234)
    second = generate_synthetic_galaxy(10_000, seed=1234)
    assert np.array_equal(first.vertices, second.vertices)
    assert first.vertices.shape == (10_000, 7)
    assert first.vertices.dtype == np.float32
    assert first.vertices.flags.c_contiguous
    assert first.byte_size == 10_000 * 7 * 4
    assert np.all(np.isfinite(first.vertices))


def test_synthetic_field_has_a_dense_core_and_extended_disk() -> None:
    field = generate_synthetic_galaxy(10_000, seed=42)
    radius = np.linalg.norm(field.vertices[:, [0, 2]], axis=1)
    assert np.quantile(radius, 0.10) < 1.5
    assert np.quantile(radius, 0.90) > 6.0
    assert np.all((field.vertices[:, 3:6] >= 0.0) & (field.vertices[:, 3:6] <= 1.0))
    assert np.all(field.vertices[:, 6] > 0.0)


def test_invalid_particle_counts_and_buffers_are_rejected() -> None:
    with pytest.raises(ValueError):
        generate_synthetic_galaxy(0)
    with pytest.raises(TypeError):
        ParticleField(np.zeros((2, 7), dtype=np.float64))
    with pytest.raises(ValueError):
        ParticleField(np.zeros((2, 6), dtype=np.float32))
    invalid = np.zeros((2, 7), dtype=np.float32)
    invalid[0, 0] = np.nan
    with pytest.raises(ValueError):
        ParticleField(invalid)
