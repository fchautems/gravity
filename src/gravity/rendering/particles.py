"""ModernGL particle renderer with one dynamic buffer and one base draw."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import moderngl
import numpy as np

from gravity.core.observation import ColorMode, ParticleObservations
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


def _normalized(values: np.ndarray, percentile: float = 95.0) -> np.ndarray:
    scale = max(float(np.percentile(np.abs(values), percentile)), 1.0e-9)
    return np.clip(values / scale, 0.0, 1.0)


def _particle_colors(
    positions: np.ndarray,
    observations: ParticleObservations | None,
    mode: ColorMode,
) -> tuple[np.ndarray, np.ndarray]:
    count = int(positions.shape[0])
    radius = np.linalg.norm(positions, axis=1).astype(np.float64)
    warm = np.array([1.0, 0.48, 0.20], dtype=np.float64)
    cool = np.array([0.28, 0.62, 1.0], dtype=np.float64)
    if observations is None or mode is ColorMode.DISTANCE:
        mix = np.clip(radius / 10.8, 0.0, 1.0)
        colors = warm[None, :] * (1.0 - mix[:, None]) + cool[None, :] * mix[:, None]
    elif mode is ColorMode.SPEED:
        mix = _normalized(observations.speeds.astype(np.float64))
        slow = np.array([0.20, 0.48, 1.0], dtype=np.float64)
        fast = np.array([1.0, 0.28, 0.08], dtype=np.float64)
        colors = slow[None, :] * (1.0 - mix[:, None]) + fast[None, :] * mix[:, None]
    elif mode is ColorMode.COMPONENT:
        palette = np.array(
            [[0.30, 0.68, 1.0], [1.0, 0.48, 0.18], [1.0, 0.94, 0.58]],
            dtype=np.float64,
        )
        colors = palette[np.minimum(observations.components, 2)]
    elif mode is ColorMode.ENERGY:
        energy = observations.specific_energies.astype(np.float64)
        scale = max(float(np.percentile(np.abs(energy), 95.0)), 1.0e-9)
        signed = np.clip(energy / scale, -1.0, 1.0)
        neutral = np.array([0.88, 0.88, 0.88], dtype=np.float64)
        bound = np.array([0.18, 0.48, 1.0], dtype=np.float64)
        free = np.array([1.0, 0.24, 0.08], dtype=np.float64)
        colors = np.empty((count, 3), dtype=np.float64)
        negative = signed < 0.0
        colors[negative] = neutral[None, :] * (1.0 + signed[negative, None]) + bound[None, :] * (
            -signed[negative, None]
        )
        colors[~negative] = (
            neutral[None, :] * (1.0 - signed[~negative, None])
            + free[None, :] * signed[~negative, None]
        )
    else:
        colors = np.tile(np.array([0.30, 0.66, 1.0], dtype=np.float64), (count, 1))
        colors[observations.ejected] = np.array([1.0, 0.20, 0.08], dtype=np.float64)

    return colors, radius


def physical_particle_field(
    positions: np.ndarray,
    observations: ParticleObservations | None = None,
    color_mode: ColorMode = ColorMode.DISTANCE,
) -> ParticleField:
    """Build visual attributes from one complete physical snapshot."""

    values = np.asarray(positions)
    if values.dtype != np.float32:
        raise TypeError("physical render positions must use float32")
    if values.ndim != 2 or values.shape[1:] != (3,) or values.shape[0] < 1:
        raise ValueError("physical render positions must have shape (N, 3)")
    if not np.all(np.isfinite(values)):
        raise ValueError("physical render positions must be finite")
    if not isinstance(color_mode, ColorMode):
        raise TypeError("color_mode must be a ColorMode")
    if observations is not None and observations.radii.shape != (values.shape[0],):
        raise ValueError("observations and positions must have the same particle count")

    count = int(values.shape[0])
    colors, radius = _particle_colors(values, observations, color_mode)

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


def center_marker_field(center: tuple[float, float, float]) -> ParticleField:
    """Build one bright marker for the current centre of mass."""

    values = np.asarray(center, dtype=np.float32)
    if values.shape != (3,) or not np.all(np.isfinite(values)):
        raise ValueError("center marker must contain three finite coordinates")
    vertices = np.array(
        [[values[0], values[1], values[2], 0.25, 1.0, 0.62, 8.0]],
        dtype=np.float32,
    )
    return ParticleField(vertices)


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

    def update_field(self, field: ParticleField) -> None:
        """Replace a complete presentation field while retaining the shader."""

        if self._released:
            raise RuntimeError("Particle renderer has already been released")
        if not isinstance(field, ParticleField):
            raise TypeError("field must be a ParticleField")
        if field.count != self._field.count:
            self._vertex_array.release()
            self._buffer.release()
            self._field = field
            self._buffer = self._context.buffer(field.vertices.tobytes())
            self._vertex_array = self._context.vertex_array(
                self._program,
                [(self._buffer, "3f 4f", "in_position", "in_color_size")],
            )
        else:
            self._field = field
            self._buffer.write(field.vertices.tobytes())
        self.upload_count += 1

    def update_positions(
        self,
        positions: np.ndarray,
        *,
        observations: ParticleObservations | None = None,
        color_mode: ColorMode = ColorMode.DISTANCE,
        reset_visuals: bool = False,
    ) -> None:
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

        rebuild = values.shape[0] != self._field.count or reset_visuals
        updated_field = physical_particle_field(values, observations, color_mode)
        if rebuild:
            self._vertex_array.release()
            self._buffer.release()
            self._field = updated_field
            self._buffer = self._context.buffer(self._field.vertices.tobytes())
            self._vertex_array = self._context.vertex_array(
                self._program,
                [(self._buffer, "3f 4f", "in_position", "in_color_size")],
            )
        else:
            self._field = updated_field
            self._buffer.write(self._field.vertices.tobytes())
        self.upload_count += 1

    def render(
        self,
        camera: OrbitCamera,
        *,
        framebuffer_width: int,
        framebuffer_height: int,
        point_scale: float,
        clear_frame: bool = True,
    ) -> None:
        if self._released:
            raise RuntimeError("Particle renderer has already been released")
        if framebuffer_width <= 0 or framebuffer_height <= 0:
            return

        self._context.viewport = (0, 0, framebuffer_width, framebuffer_height)
        if clear_frame:
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
