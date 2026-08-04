from __future__ import annotations

import numpy as np
import pytest

from gravity.rendering.camera import (
    MAX_DISTANCE,
    MAX_PITCH,
    MIN_DISTANCE,
    MIN_PITCH,
    CameraView,
    OrbitCamera,
    perspective,
)


def test_default_camera_places_its_target_on_the_view_axis() -> None:
    camera = OrbitCamera()
    target_in_view = camera.view_matrix() @ np.array([*camera.target, 1.0])
    assert target_in_view[:2] == pytest.approx([0.0, 0.0], abs=1.0e-12)
    assert target_in_view[2] == pytest.approx(-camera.distance)


def test_orbit_and_zoom_are_clamped_to_safe_ranges() -> None:
    camera = OrbitCamera()
    camera.orbit(100_000.0, 100_000.0)
    assert MIN_PITCH <= camera.pitch <= MAX_PITCH
    camera.orbit(0.0, -200_000.0)
    assert camera.pitch == pytest.approx(MAX_PITCH)

    camera.zoom(10_000.0)
    assert camera.distance == pytest.approx(MIN_DISTANCE)
    camera.zoom(-10_000.0)
    assert camera.distance == pytest.approx(MAX_DISTANCE)


def test_pan_moves_only_the_focus_point() -> None:
    camera = OrbitCamera()
    original_target = camera.target.copy()
    original_distance = camera.distance
    camera.pan(80.0, -35.0, 800)
    assert not np.array_equal(camera.target, original_target)
    assert camera.distance == original_distance


def test_mvp_payload_is_finite_column_major_float32() -> None:
    camera = OrbitCamera()
    payload = camera.mvp_bytes(16.0 / 9.0)
    values = np.frombuffer(payload, dtype=np.float32)
    assert len(payload) == 64
    assert values.shape == (16,)
    assert np.all(np.isfinite(values))


def test_canonical_views_keep_focus_and_zoom() -> None:
    camera = OrbitCamera()
    camera.target[:] = [1.0, 2.0, 3.0]
    camera.distance = 33.0
    camera.set_view(CameraView.TOP)
    assert camera.pitch == pytest.approx(MAX_PITCH)
    camera.set_view(CameraView.PROFILE)
    assert camera.pitch == pytest.approx(0.0)
    camera.set_view(CameraView.PERSPECTIVE)
    assert camera.target == pytest.approx([1.0, 2.0, 3.0])
    assert camera.distance == pytest.approx(33.0)


@pytest.mark.parametrize("aspect", [0.0, -1.0, float("nan")])
def test_projection_rejects_invalid_aspect_ratios(aspect: float) -> None:
    with pytest.raises(ValueError):
        perspective(aspect)
