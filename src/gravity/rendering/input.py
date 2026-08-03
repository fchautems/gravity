"""Camera input state kept independent from GLFW for deterministic tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from gravity.rendering.camera import OrbitCamera


class MouseButton(StrEnum):
    LEFT = "left"
    MIDDLE = "middle"
    RIGHT = "right"


class DragMode(StrEnum):
    ORBIT = "orbit"
    PAN = "pan"


@dataclass(frozen=True, slots=True)
class MouseFrame:
    position: tuple[float, float]
    pressed: frozenset[MouseButton] = field(default_factory=frozenset)
    scroll_y: float = 0.0


@dataclass(slots=True)
class CameraInputController:
    """Start drags only in the viewport and keep them latched until release."""

    _previous_position: tuple[float, float] | None = None
    _previous_pressed: frozenset[MouseButton] = field(default_factory=frozenset)
    _drag_mode: DragMode | None = None

    def update(
        self,
        camera: OrbitCamera,
        mouse: MouseFrame,
        *,
        ui_captures_mouse: bool,
        viewport_height: int,
    ) -> None:
        previous_position = self._previous_position or mouse.position
        delta_x = mouse.position[0] - previous_position[0]
        delta_y = mouse.position[1] - previous_position[1]
        newly_pressed = mouse.pressed - self._previous_pressed

        if self._drag_mode is DragMode.ORBIT and MouseButton.LEFT not in mouse.pressed:
            self._drag_mode = None
        if self._drag_mode is DragMode.PAN and not (
            {MouseButton.MIDDLE, MouseButton.RIGHT} & mouse.pressed
        ):
            self._drag_mode = None

        if self._drag_mode is None and not ui_captures_mouse:
            if MouseButton.LEFT in newly_pressed:
                self._drag_mode = DragMode.ORBIT
            elif {MouseButton.MIDDLE, MouseButton.RIGHT} & newly_pressed:
                self._drag_mode = DragMode.PAN

        if self._drag_mode is DragMode.ORBIT:
            camera.orbit(delta_x, delta_y)
        elif self._drag_mode is DragMode.PAN:
            camera.pan(delta_x, delta_y, viewport_height)

        if mouse.scroll_y and not ui_captures_mouse:
            camera.zoom(mouse.scroll_y)

        self._previous_position = mouse.position
        self._previous_pressed = mouse.pressed
