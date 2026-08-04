"""Dear ImGui control panel and compact performance overlay."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from imgui_bundle import imgui

from gravity.core.experiment import (
    MAX_EXPERIMENT_SEED,
    MAX_PARTICLE_COUNT,
    SCENARIO_CATALOG,
    ExperimentConfig,
    ScenarioKind,
    estimated_barnes_hut_load,
)
from gravity.core.simulation import SimulationStatus, SolverMode
from gravity.diagnostics.frame_stats import FrameStats
from gravity.rendering.particles import GraphicsInfo
from gravity.ui import strings


@dataclass(slots=True)
class UiState:
    panel_visible: bool = True
    point_scale: float = 1.0
    time_scale: float = 1.0
    draft_scenario: ScenarioKind = ScenarioKind.SPIRAL_GALAXY
    draft_particle_count: int = 10_000
    draft_seed: int = 2_026_080_3
    synced_generation: int = -1


@dataclass(frozen=True, slots=True)
class UiActions:
    reset_camera: bool = False
    toggle_pause: bool = False
    reset_simulation: bool = False
    single_step: bool = False
    time_scale: float | None = None
    solver_mode: SolverMode | None = None
    experiment: ExperimentConfig | None = None


def _fresh_seed(previous: int) -> int:
    candidate = secrets.randbelow(MAX_EXPERIMENT_SEED + 1)
    if candidate == previous:
        candidate = (candidate + 1) % (MAX_EXPERIMENT_SEED + 1)
    return candidate


def _synchronize_experiment_draft(state: UiState, simulation: SimulationStatus) -> None:
    if state.synced_generation == simulation.generation:
        return
    experiment = simulation.experiment_config
    state.draft_scenario = experiment.scenario
    state.draft_particle_count = experiment.particle_count
    state.draft_seed = experiment.seed
    state.synced_generation = simulation.generation


def _format_particle_count(value: int) -> str:
    return f"{value:,}".replace(",", "’")


def _panel_flags() -> imgui.WindowFlags:
    return (
        imgui.WindowFlags_.no_move
        | imgui.WindowFlags_.no_resize
        | imgui.WindowFlags_.no_collapse
        | imgui.WindowFlags_.no_saved_settings
    )


def draw_control_panel(
    state: UiState,
    stats: FrameStats,
    *,
    simulation: SimulationStatus,
    graphics: GraphicsInfo,
    window_size: tuple[int, int],
    dpi_scale: float,
) -> UiActions:
    """Draw the right panel and return discrete requests for the app controller."""

    _synchronize_experiment_draft(state, simulation)

    if not state.panel_visible:
        return _draw_settings_toggle(state, window_size, dpi_scale)

    width, height = window_size
    panel_width = min(max(315.0 * dpi_scale, 300.0), max(300.0, width * 0.44))
    imgui.set_next_window_pos((width - panel_width, 0.0), imgui.Cond_.always)
    imgui.set_next_window_size((panel_width, float(height)), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.96)

    expanded, _ = imgui.begin("Gravity##control-panel", None, _panel_flags())
    reset_camera = False
    toggle_pause = False
    reset_simulation = False
    single_step = False
    selected_time_scale = None
    selected_solver = None
    selected_experiment = None
    if expanded:
        imgui.text_colored((0.30, 0.72, 1.00, 1.00), strings.APP_NAME)
        imgui.text(simulation.experiment_config.scenario.french_name)
        imgui.text_disabled(strings.VISUAL_MILESTONE)
        imgui.spacing()
        imgui.text_wrapped(strings.PHYSICAL_NOTICE)

        imgui.separator_text(strings.CONTROLS)
        if imgui.button(
            strings.RESUME if simulation.paused else strings.PAUSE,
            (-1.0, 0.0),
        ):
            toggle_pause = True
        if imgui.button(strings.RESTART, (-1.0, 0.0)):
            reset_simulation = True
        if simulation.paused and imgui.button(strings.SINGLE_STEP, (-1.0, 0.0)):
            single_step = True
        if imgui.button(strings.RESET_CAMERA, (-1.0, 0.0)):
            reset_camera = True

        _, state.point_scale = imgui.slider_float(
            strings.POINT_SIZE,
            state.point_scale,
            0.55,
            2.4,
            "%.2f×",
        )
        speed_changed, state.time_scale = imgui.slider_float(
            strings.ANIMATION_SPEED,
            state.time_scale,
            0.1,
            2.5,
            "%.2f×",
        )
        if speed_changed:
            selected_time_scale = state.time_scale

        imgui.separator_text(strings.EXPERIMENT)
        scenario_index = SCENARIO_CATALOG.index(state.draft_scenario)
        scenario_changed, scenario_index = imgui.combo(
            strings.INITIAL_SCENARIO,
            scenario_index,
            [scenario.french_name for scenario in SCENARIO_CATALOG],
        )
        if scenario_changed:
            state.draft_scenario = SCENARIO_CATALOG[scenario_index]
            state.draft_particle_count = max(
                state.draft_particle_count,
                state.draft_scenario.minimum_particles,
            )
        imgui.text_wrapped(state.draft_scenario.french_description)

        count_changed, draft_count = imgui.input_int(
            strings.PARTICLE_COUNT,
            state.draft_particle_count,
            1_000,
            5_000,
        )
        if count_changed:
            state.draft_particle_count = min(
                MAX_PARTICLE_COUNT,
                max(state.draft_scenario.minimum_particles, draft_count),
            )
        seed_changed, draft_seed = imgui.input_int(
            strings.RANDOM_SEED,
            state.draft_seed,
            1,
            1_000,
        )
        if seed_changed:
            state.draft_seed = min(MAX_EXPERIMENT_SEED, max(0, draft_seed))

        candidate = ExperimentConfig(
            scenario=state.draft_scenario,
            particle_count=state.draft_particle_count,
            seed=state.draft_seed,
        )
        load = estimated_barnes_hut_load(candidate.particle_count)
        imgui.text_disabled(f"Charge Barnes–Hut estimée : {load:.2f}× la valeur par défaut")
        if imgui.button(strings.LAUNCH_EXPERIMENT, (-1.0, 0.0)):
            selected_experiment = candidate
        if imgui.button(strings.NEW_RANDOMIZATION, (-1.0, 0.0)):
            state.draft_seed = _fresh_seed(candidate.seed)
            selected_experiment = ExperimentConfig(
                scenario=candidate.scenario,
                particle_count=candidate.particle_count,
                seed=state.draft_seed,
            )

        imgui.separator_text(strings.PERFORMANCE)
        imgui.text(f"{stats.fps:5.1f} FPS")
        imgui.text_disabled(f"Image médiane : {stats.frame_ms:5.2f} ms")
        imgui.text_disabled(f"Rendu médian : {stats.draw_ms:5.2f} ms")
        imgui.text(f"{simulation.particle_count:,} particules".replace(",", "’"))
        imgui.text_disabled(f"Physique : {simulation.physics_ms:5.2f} ms / pas")
        simulated_time = f"{simulation.simulation_time:.2f}"
        step_count = f"{simulation.step_count:,}".replace(",", "’")
        imgui.text_disabled(f"Temps simulé : {simulated_time} · pas {step_count}")
        imgui.text_disabled("1 instantané · 1 tampon GPU · 1 appel de dessin")

        if imgui.collapsing_header(strings.ADVANCED_PHYSICS):
            imgui.text(f"Moteur : {simulation.solver_mode.french_name}")
            if simulation.solver_mode is SolverMode.BARNES_HUT:
                configured_count = _format_particle_count(
                    simulation.experiment_config.particle_count
                )
                imgui.text_disabled(f"Mode normal · Barnes–Hut · {configured_count} particules")
                imgui.text_wrapped(strings.EXACT_WARNING)
                if imgui.button(strings.EXACT_TEST, (-1.0, 0.0)):
                    selected_solver = SolverMode.EXACT
            else:
                imgui.text_colored((1.0, 0.67, 0.28, 1.0), "MODE DE COMPARAISON")
                imgui.text_wrapped(strings.EXACT_WARNING)
                if imgui.button(strings.BACK_TO_BARNES_HUT, (-1.0, 0.0)):
                    selected_solver = SolverMode.BARNES_HUT

        if imgui.collapsing_header(strings.GRAPHICS):
            imgui.text_wrapped(graphics.renderer)
            imgui.text_disabled(f"OpenGL {graphics.version_code / 100:.1f} · {graphics.vendor}")

        if imgui.collapsing_header(strings.HELP):
            imgui.text_wrapped(strings.MOUSE_HELP)

        imgui.spacing()
        if imgui.button(strings.HIDE_SETTINGS, (-1.0, 0.0)):
            state.panel_visible = False
    imgui.end()
    return UiActions(
        reset_camera=reset_camera,
        toggle_pause=toggle_pause,
        reset_simulation=reset_simulation,
        single_step=single_step,
        time_scale=selected_time_scale,
        solver_mode=selected_solver,
        experiment=selected_experiment,
    )


def _draw_settings_toggle(
    state: UiState,
    window_size: tuple[int, int],
    dpi_scale: float,
) -> UiActions:
    width, _ = window_size
    toggle_width = 118.0 * dpi_scale
    imgui.set_next_window_pos((width - toggle_width - 12.0, 12.0), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.82)
    flags = (
        imgui.WindowFlags_.always_auto_resize
        | imgui.WindowFlags_.no_decoration
        | imgui.WindowFlags_.no_move
        | imgui.WindowFlags_.no_saved_settings
    )
    expanded, _ = imgui.begin("Gravity##settings-toggle", None, flags)
    if expanded and imgui.button(strings.SHOW_SETTINGS, (toggle_width - 18.0, 0.0)):
        state.panel_visible = True
    imgui.end()
    return UiActions()


def draw_performance_overlay(stats: FrameStats) -> None:
    imgui.set_next_window_pos((12.0, 12.0), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.62)
    flags = (
        imgui.WindowFlags_.always_auto_resize
        | imgui.WindowFlags_.no_decoration
        | imgui.WindowFlags_.no_move
        | imgui.WindowFlags_.no_saved_settings
        | imgui.WindowFlags_.no_inputs
    )
    expanded, _ = imgui.begin("Gravity##performance-overlay", None, flags)
    if expanded:
        imgui.text_colored((0.42, 0.78, 1.00, 1.00), f"{stats.fps:4.0f} FPS")
        imgui.text_disabled(strings.MOUSE_HELP)
    imgui.end()
