from __future__ import annotations

import numpy as np

from gravity.rendering.camera import OrbitCamera
from gravity.rendering.input import CameraInputController, MouseButton, MouseFrame


def _frame(
    x: float,
    y: float,
    *buttons: MouseButton,
    scroll: float = 0.0,
) -> MouseFrame:
    return MouseFrame((x, y), frozenset(buttons), scroll)


def test_drag_started_over_ui_never_leaks_into_the_camera() -> None:
    camera = OrbitCamera()
    controller = CameraInputController()
    original_yaw = camera.yaw

    controller.update(
        camera,
        _frame(100.0, 100.0, MouseButton.LEFT),
        ui_captures_mouse=True,
        viewport_height=800,
    )
    controller.update(
        camera,
        _frame(180.0, 140.0, MouseButton.LEFT),
        ui_captures_mouse=False,
        viewport_height=800,
    )
    assert camera.yaw == original_yaw


def test_viewport_drag_orbits_until_release() -> None:
    camera = OrbitCamera()
    controller = CameraInputController()
    original_yaw = camera.yaw

    controller.update(
        camera,
        _frame(10.0, 10.0, MouseButton.LEFT),
        ui_captures_mouse=False,
        viewport_height=800,
    )
    controller.update(
        camera,
        _frame(45.0, 20.0, MouseButton.LEFT),
        ui_captures_mouse=True,
        viewport_height=800,
    )
    assert camera.yaw != original_yaw

    controller.update(
        camera,
        _frame(45.0, 20.0),
        ui_captures_mouse=False,
        viewport_height=800,
    )


def test_ui_capture_blocks_scroll_but_viewport_scroll_zooms() -> None:
    camera = OrbitCamera()
    controller = CameraInputController()
    original_distance = camera.distance
    controller.update(
        camera,
        _frame(0.0, 0.0, scroll=3.0),
        ui_captures_mouse=True,
        viewport_height=800,
    )
    assert camera.distance == original_distance
    controller.update(
        camera,
        _frame(0.0, 0.0, scroll=3.0),
        ui_captures_mouse=False,
        viewport_height=800,
    )
    assert camera.distance < original_distance


def test_right_drag_pans_without_changing_distance() -> None:
    camera = OrbitCamera()
    controller = CameraInputController()
    original_target = camera.target.copy()
    original_distance = camera.distance
    controller.update(
        camera,
        _frame(20.0, 20.0, MouseButton.RIGHT),
        ui_captures_mouse=False,
        viewport_height=800,
    )
    controller.update(
        camera,
        _frame(55.0, 45.0, MouseButton.RIGHT),
        ui_captures_mouse=False,
        viewport_height=800,
    )
    assert not np.array_equal(camera.target, original_target)
    assert camera.distance == original_distance
