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

type Rgb = tuple[float, float, float]

_DISTANCE_PALETTE: tuple[Rgb, ...] = (
    (1.00, 0.88, 0.18),
    (0.12, 0.92, 0.98),
    (0.18, 0.34, 1.00),
    (1.00, 0.12, 0.62),
)
_SPEED_PALETTE: tuple[Rgb, ...] = (
    (0.10, 0.95, 0.54),
    (0.08, 0.60, 1.00),
    (1.00, 0.88, 0.08),
    (1.00, 0.12, 0.06),
)
_MASS_PALETTE: tuple[Rgb, ...] = (
    (0.10, 0.72, 1.00),
    (0.96, 0.90, 0.18),
    (1.00, 0.12, 0.32),
)
_ORIGIN_PALETTE: tuple[Rgb, ...] = (
    (1.00, 0.28, 0.08),
    (0.02, 0.82, 1.00),
    (0.76, 0.22, 1.00),
    (0.34, 1.00, 0.18),
)
_ENERGY_PALETTE: tuple[Rgb, ...] = (
    (0.16, 0.20, 1.00),
    (0.04, 0.88, 1.00),
    (0.98, 0.98, 0.94),
    (1.00, 0.52, 0.06),
    (1.00, 0.08, 0.42),
)
_EJECTION_PALETTE: tuple[Rgb, ...] = (
    (0.12, 0.72, 1.00),
    (1.00, 0.16, 0.08),
)


def color_legend(mode: ColorMode) -> tuple[tuple[str, ...], tuple[Rgb, ...]]:
    """Return the exact labels and colours shown below a colour selector."""

    return {
        ColorMode.DISTANCE: (("Centre", "Périphérie"), _DISTANCE_PALETTE),
        ColorMode.SPEED: (("Lente", "Rapide"), _SPEED_PALETTE),
        ColorMode.MASS: (("Légère", "Intermédiaire", "Lourde"), _MASS_PALETTE),
        ColorMode.ORIGIN: (("Objet A", "Objet B", "Objet C+"), _ORIGIN_PALETTE),
        ColorMode.ENERGY: (("Liée", "Neutre", "Libre"), _ENERGY_PALETTE),
        ColorMode.EJECTION: (("Liées", "Éjectées"), _EJECTION_PALETTE),
    }[mode]


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


def _normalized_visible_range(
    values: np.ndarray,
    lower_percentile: float = 2.0,
    upper_percentile: float = 98.0,
) -> np.ndarray:
    """Spread the values actually present across the complete visual palette."""

    measured = np.asarray(values, dtype=np.float64)
    lower, upper = np.percentile(measured, (lower_percentile, upper_percentile))
    span = float(upper - lower)
    if span <= 1.0e-12:
        return np.full(measured.shape, 0.5, dtype=np.float64)
    return np.ascontiguousarray(
        np.clip((measured - lower) / span, 0.0, 1.0),
        dtype=np.float64,
    )


def _ranked_masses(masses: np.ndarray) -> np.ndarray:
    """Give every distinct simulated mass an equally visible colour rank."""

    _, inverse = np.unique(np.asarray(masses, dtype=np.float32), return_inverse=True)
    levels = int(np.max(inverse)) + 1
    if levels == 1:
        return np.full(inverse.shape, 0.5, dtype=np.float64)
    return inverse.astype(np.float64) / float(levels - 1)


def _sample_palette(values: np.ndarray, palette: tuple[Rgb, ...]) -> np.ndarray:
    """Interpolate a small perceptual palette for normalized values."""

    normalized = np.clip(np.asarray(values, dtype=np.float64), 0.0, 1.0)
    stops = np.asarray(palette, dtype=np.float64)
    scaled = normalized * (len(palette) - 1)
    lower = np.minimum(scaled.astype(np.int64), len(palette) - 2)
    blend = scaled - lower
    sampled = stops[lower] * (1.0 - blend[:, None]) + stops[lower + 1] * blend[:, None]
    return np.ascontiguousarray(sampled, dtype=np.float64)


def _particle_colors(
    positions: np.ndarray,
    observations: ParticleObservations | None,
    mode: ColorMode,
) -> tuple[np.ndarray, np.ndarray]:
    count = int(positions.shape[0])
    radius = np.linalg.norm(positions, axis=1).astype(np.float64)
    if observations is None or mode is ColorMode.DISTANCE:
        measured_radius = radius if observations is None else observations.radii
        colors = _sample_palette(_normalized_visible_range(measured_radius), _DISTANCE_PALETTE)
    elif mode is ColorMode.SPEED:
        colors = _sample_palette(_normalized_visible_range(observations.speeds), _SPEED_PALETTE)
    elif mode is ColorMode.MASS:
        colors = _sample_palette(_ranked_masses(observations.masses), _MASS_PALETTE)
    elif mode is ColorMode.ORIGIN:
        palette = np.asarray(_ORIGIN_PALETTE, dtype=np.float64)
        colors = palette[np.minimum(observations.origins, len(_ORIGIN_PALETTE) - 1)]
    elif mode is ColorMode.ENERGY:
        energy = observations.specific_energies.astype(np.float64)
        negative = energy < 0.0
        negative_scale = max(
            float(np.percentile(np.abs(energy[negative]), 95.0)) if np.any(negative) else 0.0,
            1.0e-9,
        )
        positive_scale = max(
            float(np.percentile(energy[~negative], 95.0)) if np.any(~negative) else 0.0,
            1.0e-9,
        )
        normalized_energy = np.empty(count, dtype=np.float64)
        normalized_energy[negative] = 0.5 * (
            1.0 - np.clip(np.abs(energy[negative]) / negative_scale, 0.0, 1.0)
        )
        normalized_energy[~negative] = 0.5 + 0.5 * np.clip(
            energy[~negative] / positive_scale,
            0.0,
            1.0,
        )
        colors = _sample_palette(normalized_energy, _ENERGY_PALETTE)
    else:
        colors = np.tile(np.asarray(_EJECTION_PALETTE[0]), (count, 1))
        colors[observations.ejected] = _EJECTION_PALETTE[1]

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
    colors *= (0.96 + 0.08 * sparkle)[:, None]
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
