from __future__ import annotations

import logging
from types import SimpleNamespace

import numpy as np

from gravity.app import graphics_app
from gravity.core.simulation import RenderSnapshot, SimulationStatus, SolverMode
from gravity.rendering.particles import GraphicsInfo
from gravity.ui.panel import UiActions


def test_cleanup_failure_is_logged_without_blocking_later_cleanup(caplog: object) -> None:
    logger = logging.getLogger("gravity.cleanup-test")

    def fail() -> None:
        raise RuntimeError("release failed")

    with caplog.at_level(logging.ERROR):  # type: ignore[attr-defined]
        graphics_app._release_safely(logger, "test resource", fail)
    assert "Failed to release test resource" in caplog.text  # type: ignore[attr-defined]


def test_graphics_loop_releases_every_owned_resource(monkeypatch: object) -> None:
    events: list[str] = []

    class FakeWindow:
        handle = object()

        def __init__(self, _logger: logging.Logger) -> None:
            self.close_checks = 0

        def open(self) -> None:
            events.append("window-open")

        def content_scale(self) -> float:
            return 1.0

        def should_close(self) -> bool:
            self.close_checks += 1
            return self.close_checks > 1

        def poll_events(self) -> None:
            events.append("poll")

        def window_size(self) -> tuple[int, int]:
            return (1280, 800)

        def framebuffer_size(self) -> tuple[int, int]:
            return (1280, 800)

        def swap_buffers(self) -> None:
            events.append("swap")

        def close(self) -> None:
            events.append("window-close")

    class FakeContext:
        def release(self) -> None:
            events.append("context-release")

    class FakeImguiRenderer:
        def __init__(self, _window: object, *, attach_callbacks: bool) -> None:
            assert not attach_callbacks

        def process_inputs(self) -> None:
            events.append("ui-input")

        def render(self, _data: object) -> None:
            events.append("ui-render")

        def shutdown(self) -> None:
            events.append("ui-release")

    class FakeInputRouter:
        def __init__(self, *_args: object) -> None:
            pass

        def attach(self) -> None:
            events.append("input-attach")

        def update_camera(self, **_kwargs: object) -> None:
            events.append("camera-input")

    class FakeParticleRenderer:
        def __init__(self, _context: object, _field: object) -> None:
            pass

        def graphics_info(self) -> GraphicsInfo:
            return GraphicsInfo(330, "GPU", "Vendor", "3.3")

        def update_positions(self, _positions: np.ndarray) -> None:
            events.append("particles-upload")

        def render(self, *_args: object, **_kwargs: object) -> None:
            events.append("particles-render")

        def release(self) -> None:
            events.append("particles-release")

    status = SimulationStatus(
        solver_mode=SolverMode.BARNES_HUT,
        particle_count=10_000,
        simulation_time=0.0,
        step_count=0,
        generation=0,
        paused=False,
        time_scale=1.0,
        physics_seconds=0.0,
    )
    snapshot = RenderSnapshot(np.zeros((10_000, 3), dtype=np.float32), status)

    class FakePhysicsWorker:
        def __init__(self, _logger: logging.Logger) -> None:
            pass

        def start(self) -> None:
            events.append("physics-start")

        def wait_for_snapshot(self) -> RenderSnapshot:
            return snapshot

        def latest_snapshot(self) -> None:
            return None

        def raise_if_failed(self) -> None:
            pass

        def shutdown(self) -> None:
            events.append("physics-release")

    fake_imgui = SimpleNamespace(
        create_context=lambda: events.append("ui-create"),
        destroy_context=lambda: events.append("ui-destroy"),
        get_io=lambda: SimpleNamespace(want_capture_mouse=False),
        new_frame=lambda: events.append("ui-frame"),
        render=lambda: events.append("ui-finish"),
        get_draw_data=lambda: object(),
    )

    monkeypatch.setattr(graphics_app, "GlfwWindow", FakeWindow)  # type: ignore[attr-defined]
    monkeypatch.setattr(graphics_app.moderngl, "create_context", lambda **_: FakeContext())  # type: ignore[attr-defined]
    monkeypatch.setattr(graphics_app, "imgui", fake_imgui)  # type: ignore[attr-defined]
    monkeypatch.setattr(graphics_app, "configure_theme", lambda _scale: None)  # type: ignore[attr-defined]
    monkeypatch.setattr(graphics_app, "GlfwRenderer", FakeImguiRenderer)  # type: ignore[attr-defined]
    monkeypatch.setattr(graphics_app, "GlfwInputRouter", FakeInputRouter)  # type: ignore[attr-defined]
    monkeypatch.setattr(graphics_app, "PhysicsWorker", FakePhysicsWorker)  # type: ignore[attr-defined]
    monkeypatch.setattr(graphics_app, "physical_particle_field", lambda _positions: object())  # type: ignore[attr-defined]
    monkeypatch.setattr(graphics_app, "ParticleRenderer", FakeParticleRenderer)  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        graphics_app,
        "draw_control_panel",
        lambda *_args, **_kwargs: UiActions(),
    )
    monkeypatch.setattr(graphics_app, "draw_performance_overlay", lambda _stats: None)  # type: ignore[attr-defined]

    graphics_app.run_graphics_app(logging.getLogger("test"))
    assert events.count("particles-render") == 1
    assert events[-6:] == [
        "physics-release",
        "particles-release",
        "ui-release",
        "ui-destroy",
        "context-release",
        "window-close",
    ]
