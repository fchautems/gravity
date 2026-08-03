"""Numerically testable orbit camera used by the OpenGL viewport."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, exp, radians, sin, tan

import numpy as np

DEFAULT_DISTANCE = 24.0
DEFAULT_YAW = radians(35.0)
DEFAULT_PITCH = radians(24.0)
MIN_DISTANCE = 2.5
MAX_DISTANCE = 90.0
MIN_PITCH = radians(-85.0)
MAX_PITCH = radians(85.0)
FIELD_OF_VIEW = radians(48.0)


def _normalized(vector: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(vector))
    if length <= 1.0e-12:
        raise ValueError("Cannot normalize a zero-length vector")
    return vector / length


def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
    """Return a right-handed row-major view matrix for column vectors."""

    forward = _normalized(target - eye)
    right = _normalized(np.cross(forward, up))
    camera_up = np.cross(right, forward)

    matrix = np.eye(4, dtype=np.float64)
    matrix[0, :3] = right
    matrix[1, :3] = camera_up
    matrix[2, :3] = -forward
    matrix[0, 3] = -float(np.dot(right, eye))
    matrix[1, 3] = -float(np.dot(camera_up, eye))
    matrix[2, 3] = float(np.dot(forward, eye))
    return matrix


def perspective(aspect_ratio: float) -> np.ndarray:
    """Return the fixed V1 perspective projection matrix."""

    if not np.isfinite(aspect_ratio) or aspect_ratio <= 0.0:
        raise ValueError("Aspect ratio must be finite and positive")

    near = 0.1
    far = 250.0
    focal = 1.0 / tan(FIELD_OF_VIEW / 2.0)
    matrix = np.zeros((4, 4), dtype=np.float64)
    matrix[0, 0] = focal / aspect_ratio
    matrix[1, 1] = focal
    matrix[2, 2] = (far + near) / (near - far)
    matrix[2, 3] = (2.0 * far * near) / (near - far)
    matrix[3, 2] = -1.0
    return matrix


@dataclass(slots=True)
class OrbitCamera:
    """Stable yaw/pitch orbit camera with distance-scaled pan and zoom."""

    target: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    distance: float = DEFAULT_DISTANCE
    yaw: float = DEFAULT_YAW
    pitch: float = DEFAULT_PITCH

    def reset(self) -> None:
        self.target = np.zeros(3, dtype=np.float64)
        self.distance = DEFAULT_DISTANCE
        self.yaw = DEFAULT_YAW
        self.pitch = DEFAULT_PITCH

    @property
    def position(self) -> np.ndarray:
        horizontal = cos(self.pitch)
        offset = np.array(
            [
                self.distance * horizontal * sin(self.yaw),
                self.distance * sin(self.pitch),
                self.distance * horizontal * cos(self.yaw),
            ],
            dtype=np.float64,
        )
        return self.target + offset

    def orbit(self, delta_x: float, delta_y: float) -> None:
        self.yaw = (self.yaw - delta_x * 0.006) % (2.0 * np.pi)
        self.pitch = float(np.clip(self.pitch - delta_y * 0.006, MIN_PITCH, MAX_PITCH))

    def zoom(self, wheel_delta: float) -> None:
        safe_delta = float(np.clip(wheel_delta, -50.0, 50.0))
        self.distance = float(
            np.clip(
                self.distance * exp(-safe_delta * 0.14),
                MIN_DISTANCE,
                MAX_DISTANCE,
            )
        )

    def pan(self, delta_x: float, delta_y: float, viewport_height: int) -> None:
        if viewport_height <= 0:
            return
        eye = self.position
        forward = _normalized(self.target - eye)
        right = _normalized(np.cross(forward, np.array([0.0, 1.0, 0.0])))
        camera_up = np.cross(right, forward)
        world_per_pixel = 2.0 * self.distance * tan(FIELD_OF_VIEW / 2.0) / viewport_height
        self.target += (-right * delta_x + camera_up * delta_y) * world_per_pixel

    def view_matrix(self) -> np.ndarray:
        return look_at(
            self.position,
            self.target,
            np.array([0.0, 1.0, 0.0], dtype=np.float64),
        )

    def projection_matrix(self, aspect_ratio: float) -> np.ndarray:
        return perspective(aspect_ratio)

    def mvp_bytes(self, aspect_ratio: float) -> bytes:
        """Return column-major float32 bytes expected by an OpenGL mat4 uniform."""

        matrix = self.projection_matrix(aspect_ratio) @ self.view_matrix()
        return np.ascontiguousarray(matrix.T, dtype=np.float32).tobytes()
