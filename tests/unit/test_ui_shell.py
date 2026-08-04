from __future__ import annotations

import pytest
from imgui_bundle import imgui

from gravity.core.experiment import ExperimentConfig, ScenarioKind
from gravity.core.simulation import SimulationStatus, SolverMode
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


def _simulation(
    *,
    paused: bool = False,
    generation: int = 0,
    experiment: ExperimentConfig | None = None,
) -> SimulationStatus:
    return SimulationStatus(
        solver_mode=SolverMode.BARNES_HUT,
        particle_count=10_000,
        simulation_time=1.25,
        step_count=42,
        generation=generation,
        paused=paused,
        time_scale=1.0,
        physics_seconds=0.011,
        experiment=experiment,
    )


def test_theme_and_complete_panel_build_without_a_gpu(imgui_context: None) -> None:
    configure_theme(1.5)
    assert imgui.get_style().window_rounding == pytest.approx(15.0)
    _begin_headless_frame()

    stats = FrameStats()
    stats.record(1.0 / 60.0, 0.003)
    actions = draw_control_panel(
        UiState(),
        stats,
        simulation=_simulation(),
        graphics=GraphicsInfo(330, "Test GPU", "Test Vendor", "3.3"),
        window_size=(1280, 800),
        dpi_scale=1.5,
    )
    draw_performance_overlay(stats)
    imgui.render()

    assert not actions.reset_camera
    assert not actions.reset_simulation
    assert actions.solver_mode is None
    assert imgui.get_draw_data().cmd_lists_count > 0


def test_hidden_panel_builds_its_settings_surface(imgui_context: None) -> None:
    configure_theme(1.0)
    _begin_headless_frame()
    state = UiState(panel_visible=False)
    actions = draw_control_panel(
        state,
        FrameStats(),
        simulation=_simulation(paused=True),
        graphics=GraphicsInfo(330, "GPU", "Vendor", "3.3"),
        window_size=(1280, 800),
        dpi_scale=1.0,
    )
    imgui.render()
    assert not actions.reset_camera
    assert not actions.reset_simulation
    assert not state.panel_visible


def test_new_generation_synchronizes_the_editable_experiment_draft(
    imgui_context: None,
) -> None:
    configure_theme(1.0)
    _begin_headless_frame()
    state = UiState(panel_visible=False)
    experiment = ExperimentConfig(ScenarioKind.RING, 5_000, 4321)
    draw_control_panel(
        state,
        FrameStats(),
        simulation=_simulation(generation=7, experiment=experiment),
        graphics=GraphicsInfo(330, "GPU", "Vendor", "3.3"),
        window_size=(1280, 800),
        dpi_scale=1.0,
    )
    imgui.render()
    assert state.draft_scenario is ScenarioKind.RING
    assert state.draft_particle_count == 5_000
    assert state.draft_seed == 4321
    assert state.synced_generation == 7
