from __future__ import annotations

import numpy as np
import pytest
from imgui_bundle import imgui
from imgui_bundle.imgui import internal

from gravity.core.experiment import ExperimentConfig, ScenarioKind
from gravity.core.observation import ObservationStats, ParticleObservations
from gravity.core.simulation import SimulationStatus, SolverMode
from gravity.diagnostics.frame_stats import FrameStats
from gravity.rendering.particles import GraphicsInfo
from gravity.ui import strings
from gravity.ui.panel import DataDrawer, UiState, draw_control_panel, draw_performance_overlay
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


def _observations(count: int = 10_000) -> ParticleObservations:
    return ParticleObservations(
        radii=np.zeros(count, dtype=np.float32),
        speeds=np.zeros(count, dtype=np.float32),
        specific_energies=np.zeros(count, dtype=np.float32),
        masses=np.ones(count, dtype=np.float32),
        components=np.zeros(count, dtype=np.uint8),
        origins=np.zeros(count, dtype=np.uint8),
        ejected=np.zeros(count, dtype=np.bool_),
        stats=ObservationStats((0.0, 0.0, 0.0), 2.5, 0.7, -0.3, 0.1, 12.0, 0),
    )


def test_theme_and_complete_panel_build_without_a_gpu(imgui_context: None) -> None:
    configure_theme(1.5)
    assert imgui.get_style().window_rounding == pytest.approx(13.5)
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
        observations=_observations(),
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


def test_data_drawers_fit_without_vertical_scrolling(imgui_context: None) -> None:
    configure_theme(1.0)
    state = UiState()
    for drawer in (
        DataDrawer.STATISTICS,
        DataDrawer.PERFORMANCE,
        DataDrawer.TECHNICAL,
        DataDrawer.MASSES,
    ):
        state.data_drawer = drawer
        for _ in range(2):
            _begin_headless_frame()
            draw_control_panel(
                state,
                FrameStats(),
                simulation=_simulation(paused=True),
                graphics=GraphicsInfo(330, "GPU", "Vendor", "3.3"),
                window_size=(1280, 800),
                dpi_scale=1.0,
                observations=_observations(),
            )
            imgui.render()
        window = internal.find_window_by_name("Gravity##data-drawer")
        assert window is not None
        assert not window.scrollbar_y
        assert window.content_size_ideal.y < window.size.y


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
    assert state.draft_disk_mass == pytest.approx(experiment.disk_mass)
    assert state.draft_bulge_mass == pytest.approx(experiment.bulge_mass)
    assert state.draft_central_mass == pytest.approx(experiment.central_mass)
    assert state.synced_generation == 7


def test_visible_ui_copy_uses_supported_ascii_apostrophes() -> None:
    visible_copy = (
        strings.SINGLE_STEP,
        strings.EXACT_TEST,
        strings.EXACT_WARNING,
    )
    assert all("’" not in text for text in visible_copy)


def test_validated_workflow_copy_replaces_the_old_restart_button() -> None:
    assert strings.CHANGE_SEED == "Changer la graine"
    assert strings.START == "Démarrer"
    assert strings.STOP == "Stop"
    assert UiState().data_drawer is DataDrawer.NONE
