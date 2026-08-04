"""ModernGL particle renderer with one dynamic buffer and one base draw."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import moderngl
import numpy as np

from gravity.rendering.camera import OrbitCamera
from gravity.rendering.shaders import FRAGMENT_SHADER, VERTEX_SHADER

VERTEX_COMPONENTS = 7


@dataclass(frozen=True, slots=True)
class ParticleField:
    """One contiguous interleaved GPU buffer: xyz, rgb, and apparent size."""

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


def physical_particle_field(positions: np.ndarray) -> ParticleField:
    """Build stable visual attributes around one physical position snapshot."""

    values = np.asarray(positions)
    if values.dtype != np.float32:
        raise TypeError("physical render positions must use float32")
    if values.ndim != 2 or values.shape[1:] != (3,) or values.shape[0] < 1:
        raise ValueError("physical render positions must have shape (N, 3)")
    if not np.all(np.isfinite(values)):
        raise ValueError("physical render positions must be finite")

    count = int(values.shape[0])
    radius = np.hypot(values[:, 0], values[:, 2]).astype(np.float64)
    radial_mix = np.clip(radius / 10.8, 0.0, 1.0)
    warm = np.array([1.0, 0.48, 0.20], dtype=np.float64)
    cool = np.array([0.28, 0.62, 1.0], dtype=np.float64)
    colors = warm[None, :] * (1.0 - radial_mix[:, None]) + cool[None, :] * radial_mix[:, None]

    indices = np.arange(count, dtype=np.uint64)
    noise = (indices * np.uint64(1_664_525) + np.uint64(1_013_904_223)) & 0xFFFF_FFFF
    sparkle = noise.astype(np.float64) / float(0xFFFF_FFFF)
    colors *= (0.91 + 0.18 * sparkle)[:, None]
    colors = np.clip(colors, 0.08, 1.0)
    sizes = 1.15 + 2.7 * np.exp(-radius / 2.6) + 0.75 * sparkle

    vertices = np.empty((count, 7), dtype=np.float32)
    vertices[:, :3] = values
    vertices[:, 3:6] = colors
    vertices[:, 6] = sizes
    return ParticleField(np.ascontiguousarray(vertices))


@dataclass(frozen=True, slots=True)
class GraphicsInfo:
    version_code: int
    renderer: str
    vendor: str
    version: str


class ParticleRenderer:
    """Own the complete dynamic GPU representation of the physical particle field."""

    def __init__(self, context: Any, field: ParticleField) -> None:
        self._context = context
        self._field = field
        self._program = context.program(
            vertex_shader=VERTEX_SHADER,
            fragment_shader=FRAGMENT_SHADER,
        )
        self._buffer = context.buffer(field.vertices.tobytes())
        self._vertex_array = context.vertex_array(
            self._program,
            [(self._buffer, "3f 4f", "in_position", "in_color_size")],
        )
        self._released = False
        self.draw_calls = 0
        self.upload_count = 1

    @property
    def particle_count(self) -> int:
        return self._field.count

    def graphics_info(self) -> GraphicsInfo:
        values = self._context.info
        return GraphicsInfo(
            version_code=int(self._context.version_code),
            renderer=str(values.get("GL_RENDERER", "inconnu")),
            vendor=str(values.get("GL_VENDOR", "inconnu")),
            version=str(values.get("GL_VERSION", "inconnue")),
        )

    def update_positions(self, positions: np.ndarray) -> None:
        """Upload one complete immutable physics snapshot to the GPU."""

        if self._released:
            raise RuntimeError("Particle renderer has already been released")
        values = np.asarray(positions)
        if values.dtype != np.float32:
            raise TypeError("render positions must use float32")
        if values.ndim != 2 or values.shape[1:] != (3,) or values.shape[0] < 1:
            raise ValueError("render positions must have shape (N, 3)")
        if not values.flags.c_contiguous or not np.all(np.isfinite(values)):
            raise ValueError("render positions must be finite and C-contiguous")

        if values.shape[0] != self._field.count:
            self._vertex_array.release()
            self._buffer.release()
            self._field = physical_particle_field(values)
            self._buffer = self._context.buffer(self._field.vertices.tobytes())
            self._vertex_array = self._context.vertex_array(
                self._program,
                [(self._buffer, "3f 4f", "in_position", "in_color_size")],
            )
        else:
            self._field.vertices[:, :3] = values
            self._buffer.write(self._field.vertices.tobytes())
        self.upload_count += 1

    def render(
        self,
        camera: OrbitCamera,
        *,
        framebuffer_width: int,
        framebuffer_height: int,
        point_scale: float,
    ) -> None:
        if self._released:
            raise RuntimeError("Particle renderer has already been released")
        if framebuffer_width <= 0 or framebuffer_height <= 0:
            return

        self._context.viewport = (0, 0, framebuffer_width, framebuffer_height)
        self._context.clear(0.006, 0.009, 0.020, 1.0)
        self._context.enable(moderngl.BLEND | moderngl.PROGRAM_POINT_SIZE)
        self._context.disable(moderngl.DEPTH_TEST)
        self._context.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE)

        aspect_ratio = framebuffer_width / framebuffer_height
        self._program["u_mvp"].write(camera.mvp_bytes(aspect_ratio))
        self._program["u_point_scale"].value = float(point_scale)
        self._vertex_array.render(mode=moderngl.POINTS, vertices=self._field.count)
        self.draw_calls += 1

    def release(self) -> None:
        if self._released:
            return
        self._vertex_array.release()
        self._buffer.release()
        self._program.release()
        self._released = True
