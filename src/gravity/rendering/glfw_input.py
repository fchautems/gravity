"""Route GLFW events to ImGui and camera controls without input conflicts."""

from __future__ import annotations

from typing import Any

import glfw

from gravity.rendering.camera import OrbitCamera
from gravity.rendering.input import CameraInputController, MouseButton, MouseFrame


class GlfwInputRouter:
    """Forward every event to ImGui while polling a presentation-only camera."""

    def __init__(
        self,
        window: Any,
        imgui_renderer: Any,
        camera: OrbitCamera,
        *,
        glfw_module: Any = glfw,
    ) -> None:
        self._window = window
        self._imgui_renderer = imgui_renderer
        self._camera = camera
        self._glfw = glfw_module
        self._camera_input = CameraInputController()
        self._scroll_y = 0.0

    def attach(self) -> None:
        self._glfw.set_key_callback(self._window, self._imgui_renderer.keyboard_callback)
        self._glfw.set_char_callback(self._window, self._imgui_renderer.char_callback)
        self._glfw.set_cursor_pos_callback(self._window, self._imgui_renderer.mouse_callback)
        self._glfw.set_mouse_button_callback(
            self._window,
            self._imgui_renderer.mouse_button_callback,
        )
        self._glfw.set_window_size_callback(self._window, self._imgui_renderer.resize_callback)
        self._glfw.set_scroll_callback(self._window, self._on_scroll)

    def _on_scroll(self, window: Any, x_offset: float, y_offset: float) -> None:
        self._imgui_renderer.scroll_callback(window, x_offset, y_offset)
        self._scroll_y += y_offset

    def update_camera(self, *, ui_captures_mouse: bool, viewport_height: int) -> None:
        x, y = self._glfw.get_cursor_pos(self._window)
        pressed: set[MouseButton] = set()
        if (
            self._glfw.get_mouse_button(self._window, self._glfw.MOUSE_BUTTON_LEFT)
            == self._glfw.PRESS
        ):
            pressed.add(MouseButton.LEFT)
        if (
            self._glfw.get_mouse_button(self._window, self._glfw.MOUSE_BUTTON_MIDDLE)
            == self._glfw.PRESS
        ):
            pressed.add(MouseButton.MIDDLE)
        if (
            self._glfw.get_mouse_button(self._window, self._glfw.MOUSE_BUTTON_RIGHT)
            == self._glfw.PRESS
        ):
            pressed.add(MouseButton.RIGHT)

        frame = MouseFrame(
            position=(float(x), float(y)),
            pressed=frozenset(pressed),
            scroll_y=self._scroll_y,
        )
        self._scroll_y = 0.0
        self._camera_input.update(
            self._camera,
            frame,
            ui_captures_mouse=ui_captures_mouse,
            viewport_height=viewport_height,
        )
