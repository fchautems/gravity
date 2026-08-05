from __future__ import annotations

from typing import Any

import moderngl
import numpy as np
import pytest

from gravity.core.observation import ColorMode, observe_particles
from gravity.core.state import ParticleState
from gravity.rendering.camera import OrbitCamera
from gravity.rendering.particles import ParticleRenderer, color_legend, physical_particle_field
from gravity.rendering.shaders import FRAGMENT_SHADER, VERTEX_SHADER


def _field(count: int) -> object:
    return physical_particle_field(np.zeros((count, 3), dtype=np.float32))


class FakeUniform:
    def __init__(self) -> None:
        self.written: bytes | None = None
        self.value: float | None = None

    def write(self, value: bytes) -> None:
        self.written = value


class FakeResource:
    def __init__(self) -> None:
        self.released = False
        self.writes: list[bytes] = []

    def write(self, value: bytes) -> None:
        self.writes.append(value)

    def release(self) -> None:
        self.released = True


class FakeProgram(FakeResource):
    def __init__(self) -> None:
        super().__init__()
        self.uniforms = {
            "u_mvp": FakeUniform(),
            "u_point_scale": FakeUniform(),
        }

    def __getitem__(self, name: str) -> FakeUniform:
        return self.uniforms[name]


class FakeVertexArray(FakeResource):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[int, int]] = []

    def render(self, *, mode: int, vertices: int) -> None:
        self.calls.append((mode, vertices))


class FakeContext:
    version_code = 330
    info = {
        "GL_RENDERER": "Test GPU",
        "GL_VENDOR": "Gravity",
        "GL_VERSION": "3.3 test",
    }

    def __init__(self) -> None:
        self.program_resource = FakeProgram()
        self.buffer_resource = FakeResource()
        self.vertex_array_resource = FakeVertexArray()
        self.viewport: tuple[int, int, int, int] | None = None
        self.blend_func: tuple[int, int] | None = None
        self.clear_calls: list[tuple[float, float, float, float]] = []
        self.enabled: list[int] = []
        self.disabled: list[int] = []
        self.buffer_bytes: bytes | None = None
        self.vertex_layout: list[Any] | None = None

    def program(self, **_shaders: str) -> FakeProgram:
        return self.program_resource

    def buffer(self, value: bytes) -> FakeResource:
        self.buffer_bytes = value
        return self.buffer_resource

    def vertex_array(
        self,
        _program: FakeProgram,
        layout: list[Any],
    ) -> FakeVertexArray:
        self.vertex_layout = layout
        return self.vertex_array_resource

    def clear(self, red: float, green: float, blue: float, alpha: float) -> None:
        self.clear_calls.append((red, green, blue, alpha))

    def enable(self, flags: int) -> None:
        self.enabled.append(flags)

    def disable(self, flags: int) -> None:
        self.disabled.append(flags)


def test_renderer_uploads_once_and_draws_all_particles_once_per_frame() -> None:
    context = FakeContext()
    field = _field(64)
    renderer = ParticleRenderer(context, field)  # type: ignore[arg-type]
    assert context.buffer_bytes == field.vertices.tobytes()
    assert context.vertex_layout is not None
    assert len(context.vertex_layout) == 1

    renderer.render(
        OrbitCamera(),
        framebuffer_width=1280,
        framebuffer_height=720,
        point_scale=1.2,
    )
    assert context.vertex_array_resource.calls == [(moderngl.POINTS, 64)]
    assert renderer.draw_calls == 1
    assert context.viewport == (0, 0, 1280, 720)
    assert len(context.program_resource["u_mvp"].written or b"") == 64
    assert context.program_resource["u_point_scale"].value == pytest.approx(1.2)


def test_zero_size_framebuffer_skips_draw_and_release_is_idempotent() -> None:
    context = FakeContext()
    renderer = ParticleRenderer(context, _field(8))  # type: ignore[arg-type]
    renderer.render(
        OrbitCamera(),
        framebuffer_width=0,
        framebuffer_height=720,
        point_scale=1.0,
    )
    assert context.vertex_array_resource.calls == []
    renderer.release()
    renderer.release()
    assert context.vertex_array_resource.released
    assert context.buffer_resource.released
    assert context.program_resource.released
    with pytest.raises(RuntimeError):
        renderer.render(
            OrbitCamera(),
            framebuffer_width=10,
            framebuffer_height=10,
            point_scale=1.0,
        )


def test_overlay_render_does_not_clear_the_existing_particle_field() -> None:
    context = FakeContext()
    renderer = ParticleRenderer(context, _field(1))  # type: ignore[arg-type]
    renderer.render(
        OrbitCamera(),
        framebuffer_width=640,
        framebuffer_height=480,
        point_scale=1.0,
        clear_frame=False,
    )
    assert context.clear_calls == []
    assert context.vertex_array_resource.calls == [(moderngl.POINTS, 1)]
    renderer.release()


def test_physics_snapshots_update_or_resize_the_single_gpu_buffer() -> None:
    context = FakeContext()
    initial = np.zeros((8, 3), dtype=np.float32)
    renderer = ParticleRenderer(context, physical_particle_field(initial))

    moved = np.full((8, 3), 0.25, dtype=np.float32)
    renderer.update_positions(moved)
    assert context.buffer_resource.writes
    assert renderer.particle_count == 8
    assert renderer.upload_count == 2

    resized = np.zeros((4, 3), dtype=np.float32)
    old_buffer = context.buffer_resource
    renderer.update_positions(resized)
    assert old_buffer.released
    assert renderer.particle_count == 4
    assert renderer.upload_count == 3
    renderer.release()


def test_new_generation_rebuilds_visual_attributes_even_when_count_is_unchanged() -> None:
    context = FakeContext()
    initial = np.zeros((8, 3), dtype=np.float32)
    renderer = ParticleRenderer(context, physical_particle_field(initial))
    old_buffer = context.buffer_resource

    moved = np.full((8, 3), 4.0, dtype=np.float32)
    renderer.update_positions(moved, reset_visuals=True)
    assert old_buffer.released
    assert renderer.particle_count == 8
    assert renderer.upload_count == 2
    renderer.release()


def test_graphics_info_and_shader_contract() -> None:
    renderer = ParticleRenderer(FakeContext(), _field(2))  # type: ignore[arg-type]
    info = renderer.graphics_info()
    assert info.version_code == 330
    assert info.renderer == "Test GPU"
    assert "#version 330 core" in VERTEX_SHADER
    assert "u_time" not in VERTEX_SHADER
    assert "gl_PointSize" in VERTEX_SHADER
    assert "gl_PointCoord" in FRAGMENT_SHADER
    renderer.release()


def test_physical_colour_modes_encode_distinct_observations() -> None:
    positions64 = np.array(
        [[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [20.0, 0.0, 0.0]],
        dtype=np.float64,
    )
    state = ParticleState.from_arrays(
        positions64,
        [[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [2.0, 0.0, 0.0]],
        [0.2, 0.3, 0.5],
    )
    observations = observe_particles(
        state,
        np.array([0, 1, 2], dtype=np.uint8),
        np.array([0, 1, 2], dtype=np.uint8),
        (),
        softening=0.08,
        ejection_radius=10.0,
        reference_energy=None,
    )
    positions = np.ascontiguousarray(positions64, dtype=np.float32)
    distance = physical_particle_field(positions, observations, ColorMode.DISTANCE)
    speed = physical_particle_field(positions, observations, ColorMode.SPEED)
    mass = physical_particle_field(positions, observations, ColorMode.MASS)
    origin = physical_particle_field(positions, observations, ColorMode.ORIGIN)
    energy = physical_particle_field(positions, observations, ColorMode.ENERGY)
    ejection = physical_particle_field(positions, observations, ColorMode.EJECTION)
    assert not np.array_equal(distance.vertices[:, 3:6], speed.vertices[:, 3:6])
    assert len(np.unique(mass.vertices[:, 3:6], axis=0)) == 3
    assert len(np.unique(origin.vertices[:, 3:6], axis=0)) == 3
    assert np.all(np.isfinite(energy.vertices[:, 3:6]))
    ejected_index = int(np.flatnonzero(observations.ejected)[0])
    assert ejection.vertices[ejected_index, 3] > ejection.vertices[ejected_index, 5]


def test_continuous_colour_modes_use_the_full_visible_range() -> None:
    positions = np.array(
        [[5.0, 0.0, 0.0], [6.0, 0.0, 0.0], [7.0, 0.0, 0.0], [8.0, 0.0, 0.0]],
        dtype=np.float32,
    )
    field = physical_particle_field(positions, color_mode=ColorMode.DISTANCE)
    colours = field.vertices[:, 3:6]
    assert np.ptp(colours[:, 0]) > 0.5
    assert np.ptp(colours[:, 1]) > 0.4
    assert np.ptp(colours[:, 2]) > 0.5


def test_each_colour_mode_exposes_a_distinct_readable_legend() -> None:
    palettes = []
    for mode in ColorMode:
        labels, palette = color_legend(mode)
        assert len(labels) >= 2
        assert len(palette) >= 2
        assert len(set(palette)) == len(palette)
        palettes.append(palette)
    assert len(set(palettes)) == len(ColorMode)
