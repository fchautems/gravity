from __future__ import annotations

import pytest
from imgui_bundle import imgui

from gravity.app.animation import AnimationClock
from gravity.diagnostics.frame_stats import FrameStats
from gravity.rendering.particles import GraphicsInfo
from gravity.ui.panel import UiState, draw_control_panel, draw_performance_overlay
from gravity.ui.theme import configure_theme


@pytest.fixture
def imgui_context() -> None:
    imgui.create_context()
    try:
        yield
    finally:
        imgui.destroy_context()


def _begin_headless_frame() -> None:
    io = imgui.get_io()
    io.display_size = (1280.0, 800.0)
    io.delta_time = 1.0 / 60.0
    io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
    imgui.new_frame()


def test_theme_and_complete_panel_build_without_a_gpu(imgui_context: None) -> None:
    configure_theme(1.5)
    assert imgui.get_style().window_rounding == pytest.approx(15.0)
    _begin_headless_frame()

    stats = FrameStats()
    stats.record(1.0 / 60.0, 0.003)
    actions = draw_control_panel(
        UiState(),
        AnimationClock(),
        stats,
        particle_count=10_000,
        graphics=GraphicsInfo(330, "Test GPU", "Test Vendor", "3.3"),
        window_size=(1280, 800),
        dpi_scale=1.5,
    )
    draw_performance_overlay(stats)
    imgui.render()

    assert not actions.reset_camera
    assert not actions.restart_animation
    assert imgui.get_draw_data().cmd_lists_count > 0


def test_hidden_panel_builds_its_settings_surface(imgui_context: None) -> None:
    configure_theme(1.0)
    _begin_headless_frame()
    state = UiState(panel_visible=False)
    actions = draw_control_panel(
        state,
        AnimationClock(),
        FrameStats(),
        particle_count=10_000,
        graphics=GraphicsInfo(330, "GPU", "Vendor", "3.3"),
        window_size=(1280, 800),
        dpi_scale=1.0,
    )
    imgui.render()
    assert not actions.reset_camera
    assert not actions.restart_animation
    assert not state.panel_visible
