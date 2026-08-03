from __future__ import annotations

from typing import Any

import moderngl
import pytest

from gravity.rendering.camera import OrbitCamera
from gravity.rendering.particles import ParticleRenderer
from gravity.rendering.shaders import FRAGMENT_SHADER, VERTEX_SHADER
from gravity.scenarios.synthetic import generate_synthetic_galaxy


class FakeUniform:
    def __init__(self) -> None:
        self.written: bytes | None = None
        self.value: float | None = None

    def write(self, value: bytes) -> None:
        self.written = value


class FakeResource:
    def __init__(self) -> None:
        self.released = False

    def release(self) -> None:
        self.released = True


class FakeProgram(FakeResource):
    def __init__(self) -> None:
        super().__init__()
        self.uniforms = {
            "u_mvp": FakeUniform(),
            "u_time": FakeUniform(),
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
    field = generate_synthetic_galaxy(64, seed=7)
    renderer = ParticleRenderer(context, field)
    assert context.buffer_bytes == field.vertices.tobytes()
    assert context.vertex_layout is not None
    assert len(context.vertex_layout) == 1

    renderer.render(
        OrbitCamera(),
        framebuffer_width=1280,
        framebuffer_height=720,
        animation_time=2.5,
        point_scale=1.2,
    )
    assert context.vertex_array_resource.calls == [(moderngl.POINTS, 64)]
    assert renderer.draw_calls == 1
    assert context.viewport == (0, 0, 1280, 720)
    assert len(context.program_resource["u_mvp"].written or b"") == 64
    assert context.program_resource["u_time"].value == 2.5
    assert context.program_resource["u_point_scale"].value == pytest.approx(1.2)


def test_zero_size_framebuffer_skips_draw_and_release_is_idempotent() -> None:
    context = FakeContext()
    renderer = ParticleRenderer(context, generate_synthetic_galaxy(8))
    renderer.render(
        OrbitCamera(),
        framebuffer_width=0,
        framebuffer_height=720,
        animation_time=0.0,
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
            animation_time=0.0,
            point_scale=1.0,
        )


def test_graphics_info_and_shader_contract() -> None:
    renderer = ParticleRenderer(FakeContext(), generate_synthetic_galaxy(2))
    info = renderer.graphics_info()
    assert info.version_code == 330
    assert info.renderer == "Test GPU"
    assert "#version 330 core" in VERTEX_SHADER
    assert "gl_PointSize" in VERTEX_SHADER
    assert "gl_PointCoord" in FRAGMENT_SHADER
    renderer.release()
