"""ModernGL particle renderer with one interleaved buffer and one base draw."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import moderngl

from gravity.rendering.camera import OrbitCamera
from gravity.rendering.shaders import FRAGMENT_SHADER, VERTEX_SHADER
from gravity.scenarios.synthetic import ParticleField


@dataclass(frozen=True, slots=True)
class GraphicsInfo:
    version_code: int
    renderer: str
    vendor: str
    version: str


class ParticleRenderer:
    """Own the complete GPU representation of the synthetic particle field."""

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

    def render(
        self,
        camera: OrbitCamera,
        *,
        framebuffer_width: int,
        framebuffer_height: int,
        animation_time: float,
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
        self._program["u_time"].value = float(animation_time)
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
