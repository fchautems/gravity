"""Dear ImGui control panel arranged around the user's simulation workflow."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import StrEnum

from imgui_bundle import imgui

from gravity.core.experiment import (
    DEFAULT_BULGE_MASS,
    DEFAULT_CENTRAL_MASS,
    DEFAULT_DISK_MASS,
    MAX_CENTRAL_MASS,
    MAX_EXPERIMENT_SEED,
    MAX_EXTENDED_MASS,
    MAX_PARTICLE_COUNT,
    MIN_EXTENDED_MASS,
    SCENARIO_CATALOG,
    ExperimentConfig,
    ScenarioKind,
    estimated_barnes_hut_load,
)
from gravity.core.observation import ColorMode, ParticleObservations
from gravity.core.simulation import SimulationStatus, SolverMode
from gravity.diagnostics.frame_stats import FrameStats
from gravity.rendering.camera import CameraView
from gravity.rendering.particles import GraphicsInfo, color_legend
from gravity.ui import strings


class DataDrawer(StrEnum):
    """Optional detail surface anchored above the panel dock."""

    NONE = "none"
    MASSES = "masses"
    STATISTICS = "statistics"
    PERFORMANCE = "performance"
    TECHNICAL = "technical"


@dataclass(slots=True)
class UiState:
    panel_visible: bool = True
    point_scale: float = 1.0
    time_scale: float = 1.0
    draft_scenario: ScenarioKind = ScenarioKind.SPIRAL_GALAXY
    draft_particle_count: int = 10_000
    draft_seed: int = 2_026_080_3
    draft_disk_mass: float = DEFAULT_DISK_MASS
    draft_bulge_mass: float = DEFAULT_BULGE_MASS
    draft_central_mass: float = DEFAULT_CENTRAL_MASS
    synced_generation: int = -1
    color_mode: ColorMode = ColorMode.DISTANCE
    camera_view: CameraView = CameraView.PERSPECTIVE
    show_center_of_mass: bool = False
    data_drawer: DataDrawer = DataDrawer.NONE


@dataclass(frozen=True, slots=True)
class UiActions:
    reset_camera: bool = False
    start_simulation: bool = False
    stop_simulation: bool = False
    toggle_pause: bool = False
    reset_simulation: bool = False
    single_step: bool = False
    time_scale: float | None = None
    solver_mode: SolverMode | None = None
    experiment: ExperimentConfig | None = None
    camera_view: CameraView | None = None


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
    state.draft_disk_mass = experiment.disk_mass
    state.draft_bulge_mass = experiment.bulge_mass
    state.draft_central_mass = experiment.central_mass
    state.synced_generation = simulation.generation


def _format_particle_count(value: int) -> str:
    return f"{value:,}".replace(",", "'")


def _panel_flags() -> imgui.WindowFlags:
    return (
        imgui.WindowFlags_.no_move
        | imgui.WindowFlags_.no_resize
        | imgui.WindowFlags_.no_collapse
        | imgui.WindowFlags_.no_saved_settings
        | imgui.WindowFlags_.no_scrollbar
        | imgui.WindowFlags_.no_scroll_with_mouse
    )


def _simulation_phase(simulation: SimulationStatus) -> str:
    if simulation.paused and simulation.step_count == 0:
        return strings.STATUS_PREVIEW
    if simulation.paused:
        return strings.STATUS_PAUSED
    return strings.STATUS_RUNNING


def _section_title(number: int, label: str) -> None:
    imgui.separator_text(f"{number:02d}   {label.upper()}")


def _colored_button(
    label: str,
    size: tuple[float, float],
    colors: tuple[tuple[float, float, float, float], ...],
) -> bool:
    for slot, color in zip(
        (imgui.Col_.button, imgui.Col_.button_hovered, imgui.Col_.button_active),
        colors,
        strict=True,
    ):
        imgui.push_style_color(slot, color)
    clicked = imgui.button(label, size)
    imgui.pop_style_color(3)
    return clicked


def _draw_header(simulation: SimulationStatus) -> None:
    imgui.text_colored((0.39, 0.75, 1.00, 1.00), strings.APP_NAME)
    imgui.same_line()
    phase = _simulation_phase(simulation)
    phase_color = {
        strings.STATUS_PREVIEW: (0.45, 0.78, 1.00, 1.00),
        strings.STATUS_RUNNING: (0.40, 0.90, 0.67, 1.00),
        strings.STATUS_PAUSED: (1.00, 0.70, 0.32, 1.00),
    }[phase]
    imgui.text_colored(phase_color, f"•  {phase}")
    imgui.text_disabled(strings.VISUAL_MILESTONE)


def _draw_experiment(
    state: UiState,
    simulation: SimulationStatus,
    *,
    compact: bool,
) -> tuple[ExperimentConfig | None, bool]:
    _section_title(1, strings.EXPERIMENT)
    preview = simulation.paused and simulation.step_count == 0
    changed = False

    imgui.begin_disabled(not preview)
    imgui.text(strings.INITIAL_SCENARIO)
    imgui.set_next_item_width(-1.0)
    scenario_index = SCENARIO_CATALOG.index(state.draft_scenario)
    scenario_changed, scenario_index = imgui.combo(
        "##initial-scenario",
        scenario_index,
        [scenario.french_name for scenario in SCENARIO_CATALOG],
    )
    if scenario_changed:
        state.draft_scenario = SCENARIO_CATALOG[scenario_index]
        state.draft_particle_count = max(
            state.draft_particle_count,
            state.draft_scenario.minimum_particles,
        )
        changed = True
    if not compact:
        imgui.push_style_color(imgui.Col_.text, (0.52, 0.58, 0.70, 1.00))
        imgui.text_wrapped(state.draft_scenario.french_description)
        imgui.pop_style_color()

    table_flags = imgui.TableFlags_.sizing_stretch_same
    if imgui.begin_table("##experiment-fields", 2, table_flags):
        imgui.table_next_column()
        imgui.text(strings.PARTICLE_COUNT.replace(" Barnes–Hut", ""))
        imgui.set_next_item_width(-1.0)
        count_changed, draft_count = imgui.input_int(
            "##particle-count",
            state.draft_particle_count,
            1_000,
            5_000,
        )
        if count_changed:
            state.draft_particle_count = min(
                MAX_PARTICLE_COUNT,
                max(state.draft_scenario.minimum_particles, draft_count),
            )
            changed = True

        imgui.table_next_column()
        imgui.text(strings.RANDOM_SEED.replace(" aléatoire", ""))
        seed_button_width = 34.0
        seed_input_width = max(40.0, imgui.get_content_region_avail().x - seed_button_width - 6.0)
        imgui.set_next_item_width(seed_input_width)
        seed_changed, draft_seed = imgui.input_int(
            "##random-seed",
            state.draft_seed,
            1,
            1_000,
        )
        if seed_changed:
            state.draft_seed = min(MAX_EXPERIMENT_SEED, max(0, draft_seed))
            changed = True
        imgui.same_line()
        if imgui.button("↻##new-seed", (seed_button_width, 0.0)):
            state.draft_seed = _fresh_seed(state.draft_seed)
            changed = True
        if imgui.is_item_hovered():
            imgui.set_tooltip(strings.CHANGE_SEED)
        imgui.end_table()
    imgui.end_disabled()

    candidate = ExperimentConfig(
        scenario=state.draft_scenario,
        particle_count=state.draft_particle_count,
        seed=state.draft_seed,
        disk_mass=state.draft_disk_mass,
        bulge_mass=state.draft_bulge_mass,
        central_mass=state.draft_central_mass,
    )
    load = estimated_barnes_hut_load(candidate.particle_count)
    imgui.text_disabled(f"Charge Barnes–Hut estimée : {load:.2f}x")
    imgui.same_line()
    imgui.begin_disabled(not candidate.uses_galaxy_components)
    if imgui.small_button("Masses avancées…"):
        state.data_drawer = DataDrawer.MASSES
    imgui.end_disabled()
    if not candidate.uses_galaxy_components and imgui.is_item_hovered(
        imgui.HoveredFlags_.allow_when_disabled
    ):
        imgui.set_tooltip("Disponible pour les galaxies et les collisions.")

    imgui.begin_disabled(not preview)
    start = _colored_button(
        strings.START.upper(),
        (-1.0, 34.0),
        (
            (0.10, 0.45, 0.74, 1.00),
            (0.12, 0.56, 0.89, 1.00),
            (0.16, 0.64, 0.96, 1.00),
        ),
    )
    imgui.end_disabled()
    selected = candidate if preview and (changed or start) else None
    return selected, start


def _draw_transport(
    state: UiState,
    simulation: SimulationStatus,
) -> tuple[bool, bool, bool, float | None]:
    _section_title(2, strings.CONTROLS)
    preview = simulation.paused and simulation.step_count == 0
    spacing = imgui.get_style().item_spacing.x
    button_width = (imgui.get_content_region_avail().x - 2.0 * spacing) / 3.0

    imgui.begin_disabled(preview)
    stopped = _colored_button(
        strings.STOP,
        (button_width, 30.0),
        (
            (0.28, 0.09, 0.12, 0.82),
            (0.42, 0.12, 0.16, 0.92),
            (0.52, 0.15, 0.19, 1.00),
        ),
    )
    imgui.same_line()
    pause_label = strings.RESUME if simulation.paused else strings.PAUSE
    toggled = imgui.button(pause_label, (button_width, 30.0))
    imgui.end_disabled()
    imgui.same_line()
    centered = imgui.button("Recentrer", (button_width, 30.0))

    imgui.text(strings.ANIMATION_SPEED)
    imgui.set_next_item_width(-1.0)
    speed_changed, state.time_scale = imgui.slider_float(
        "##simulation-speed",
        state.time_scale,
        0.1,
        2.5,
        "%.2fx",
    )
    imgui.text_disabled(
        f"Demandée {simulation.time_scale:.2f}x  ·  réelle {simulation.effective_time_scale:.2f}x"
    )

    imgui.text(strings.POINT_SIZE)
    imgui.set_next_item_width(-1.0)
    _, state.point_scale = imgui.slider_float(
        "##point-size",
        state.point_scale,
        0.55,
        2.4,
        "%.2fx",
    )
    return stopped, toggled, centered, state.time_scale if speed_changed else None


def _draw_color_legend(mode: ColorMode, dpi_scale: float) -> None:
    labels, palette = color_legend(mode)
    position = imgui.get_cursor_screen_pos()
    width = imgui.get_content_region_avail().x
    height = max(5.0, 6.0 * dpi_scale)
    draw_list = imgui.get_window_draw_list()
    segment_width = width / (len(palette) - 1)
    for index in range(len(palette) - 1):
        left = position.x + index * segment_width
        right = position.x + (index + 1) * segment_width
        first = imgui.get_color_u32((*palette[index], 1.0))
        second = imgui.get_color_u32((*palette[index + 1], 1.0))
        draw_list.add_rect_filled_multi_color(
            (left, position.y),
            (right, position.y + height),
            first,
            second,
            second,
            first,
        )
    imgui.invisible_button("##color-legend", (width, height))
    if imgui.begin_table(
        "##color-legend-labels", len(labels), imgui.TableFlags_.sizing_stretch_same
    ):
        for label in labels:
            imgui.table_next_column()
            imgui.text_disabled(label)
        imgui.end_table()


def _view_button(label: str, active: bool, width: float) -> bool:
    if active:
        return _colored_button(
            label,
            (width, 28.0),
            (
                (0.10, 0.29, 0.46, 1.00),
                (0.13, 0.39, 0.60, 1.00),
                (0.16, 0.47, 0.70, 1.00),
            ),
        )
    return imgui.button(label, (width, 28.0))


def _draw_observation(
    state: UiState,
    simulation: SimulationStatus,
    observations: ParticleObservations | None,
    dpi_scale: float,
) -> CameraView | None:
    _section_title(3, strings.OBSERVATION)
    imgui.text(strings.COLOR_MODE)
    imgui.set_next_item_width(-1.0)
    color_modes = list(ColorMode)
    color_index = color_modes.index(state.color_mode)
    imgui.push_style_color(imgui.Col_.text, (0.96, 0.98, 1.00, 1.00))
    changed, color_index = imgui.combo(
        "##color-mode", color_index, [mode.french_name for mode in color_modes]
    )
    imgui.pop_style_color()
    if changed:
        state.color_mode = color_modes[color_index]
    _draw_color_legend(state.color_mode, dpi_scale)

    _, state.show_center_of_mass = imgui.checkbox(
        strings.SHOW_CENTER,
        state.show_center_of_mass,
    )
    if observations is not None:
        ejected = observations.stats.ejected_count
        linked = simulation.particle_count - ejected
        imgui.same_line()
        imgui.text_colored(
            (0.70, 0.80, 0.92, 1.00),
            f"{_format_particle_count(linked)} liées",
        )
        imgui.same_line()
        imgui.text_colored((1.00, 0.48, 0.34, 1.00), f"· {ejected} éjectées")

    imgui.text("Point de vue")
    spacing = imgui.get_style().item_spacing.x
    button_width = (imgui.get_content_region_avail().x - 2.0 * spacing) / 3.0
    selected_view = None
    for index, view in enumerate(CameraView):
        if index:
            imgui.same_line()
        if _view_button(view.french_name, state.camera_view is view, button_width):
            state.camera_view = view
            selected_view = view

    return selected_view


def _drawer_button(label: str, drawer: DataDrawer, state: UiState, width: float) -> None:
    active = state.data_drawer == drawer
    clicked = _view_button(label, active, width)
    if clicked:
        state.data_drawer = DataDrawer.NONE if state.data_drawer == drawer else drawer


def _draw_data_dock(state: UiState) -> float:
    dock_top_y = imgui.get_cursor_screen_pos().y
    spacing = imgui.get_style().item_spacing.x
    width = (imgui.get_content_region_avail().x - 2.0 * spacing) / 3.0
    _drawer_button("Statistiques", DataDrawer.STATISTICS, state, width)
    imgui.same_line()
    _drawer_button("Performances", DataDrawer.PERFORMANCE, state, width)
    imgui.same_line()
    _drawer_button("Technique", DataDrawer.TECHNICAL, state, width)
    return dock_top_y


def _metric(label: str, value: str, *, accent: bool = False) -> None:
    imgui.text_disabled(label)
    if accent:
        imgui.text_colored((0.46, 0.82, 1.00, 1.00), value)
    else:
        imgui.text(value)


def _draw_statistics_drawer(observations: ParticleObservations | None) -> None:
    if observations is None:
        imgui.text_disabled("Les statistiques seront disponibles au prochain instantané.")
        return
    physical = observations.stats
    if imgui.begin_table("##physical-metrics", 2, imgui.TableFlags_.sizing_stretch_same):
        imgui.table_next_column()
        _metric("Rayon médian", f"{physical.median_radius:.2f}")
        imgui.table_next_column()
        _metric("Vitesse maximale", f"{physical.max_speed:.3f}")
        imgui.table_next_column()
        _metric("Énergie estimée", f"{physical.estimated_energy:.5f}", accent=True)
        imgui.table_next_column()
        _metric("Dérive estimée", f"{physical.energy_drift_percent:+.2f} %")
        imgui.table_next_column()
        _metric("Seuil d'éjection", f"{physical.ejection_radius:.2f}")
        imgui.table_next_column()
        _metric("Centre de masse", " · ".join(f"{value:+.3f}" for value in physical.center_of_mass))
        imgui.end_table()
    imgui.text_disabled("Énergie et éjections : estimations monopôles en O(N).")


def _draw_performance_drawer(stats: FrameStats, simulation: SimulationStatus) -> None:
    if imgui.begin_table("##performance-metrics", 2, imgui.TableFlags_.sizing_stretch_same):
        imgui.table_next_column()
        _metric("Fréquence d'image", f"{stats.fps:.1f} FPS", accent=True)
        imgui.table_next_column()
        _metric("Image médiane", f"{stats.frame_ms:.2f} ms")
        imgui.table_next_column()
        _metric("Calcul physique", f"{simulation.physics_ms:.2f} ms / pas")
        imgui.table_next_column()
        _metric("Rendu médian", f"{stats.draw_ms:.2f} ms")
        imgui.table_next_column()
        _metric("Temps simulé", f"{simulation.simulation_time:.2f}")
        imgui.table_next_column()
        _metric("Pas calculés", _format_particle_count(simulation.step_count))
        imgui.end_table()
    imgui.text_disabled(
        f"Demandée {simulation.time_scale:.2f}x · réelle {simulation.effective_time_scale:.2f}x"
    )


def _draw_technical_drawer(
    simulation: SimulationStatus,
    graphics: GraphicsInfo,
) -> SolverMode | None:
    imgui.text(f"Moteur physique   {simulation.solver_mode.french_name}")
    imgui.text_disabled(
        f"{_format_particle_count(simulation.particle_count)} particules réellement simulées"
    )
    imgui.text(f"Carte graphique   OpenGL {graphics.version_code / 100:.1f}")
    imgui.text_disabled(graphics.renderer)
    imgui.separator()
    selected_solver = None
    if simulation.solver_mode is SolverMode.BARNES_HUT:
        imgui.text_wrapped(strings.EXACT_WARNING)
        if imgui.button(strings.EXACT_TEST, (-1.0, 0.0)):
            selected_solver = SolverMode.EXACT
    else:
        imgui.text_colored((1.00, 0.67, 0.28, 1.00), "MODE DE COMPARAISON")
        if imgui.button(strings.BACK_TO_BARNES_HUT, (-1.0, 0.0)):
            selected_solver = SolverMode.BARNES_HUT
    imgui.separator()
    imgui.text_disabled(strings.MOUSE_HELP)
    imgui.text_disabled(strings.KEYBOARD_HELP)
    return selected_solver


def _draw_mass_drawer(
    state: UiState,
    simulation: SimulationStatus,
) -> ExperimentConfig | None:
    preview = simulation.paused and simulation.step_count == 0
    applicable = state.draft_scenario in (
        ScenarioKind.SPIRAL_GALAXY,
        ScenarioKind.HEAD_ON_COLLISION,
        ScenarioKind.OBLIQUE_COLLISION,
    )
    imgui.text_wrapped(
        "Masses totales du système. Dans une collision, elles sont réparties entre les galaxies."
    )
    imgui.begin_disabled(not preview or not applicable)
    imgui.text("Disque")
    imgui.set_next_item_width(-1.0)
    changed, value = imgui.input_float(
        "##disk-mass",
        state.draft_disk_mass,
        0.05,
        0.25,
        "%.3f",
    )
    if changed:
        state.draft_disk_mass = min(MAX_EXTENDED_MASS, max(MIN_EXTENDED_MASS, value))
    imgui.text("Bulbe")
    imgui.set_next_item_width(-1.0)
    changed, value = imgui.input_float(
        "##bulge-mass",
        state.draft_bulge_mass,
        0.05,
        0.25,
        "%.3f",
    )
    if changed:
        state.draft_bulge_mass = min(MAX_EXTENDED_MASS, max(MIN_EXTENDED_MASS, value))
    imgui.text("Centre")
    imgui.set_next_item_width(-1.0)
    changed, value = imgui.input_float(
        "##central-mass",
        state.draft_central_mass,
        0.01,
        0.05,
        "%.3f",
    )
    if changed:
        state.draft_central_mass = min(MAX_CENTRAL_MASS, max(0.0, value))

    spacing = imgui.get_style().item_spacing.x
    button_width = (imgui.get_content_region_avail().x - spacing) / 2.0
    if imgui.button("Valeurs par défaut", (button_width, 0.0)):
        state.draft_disk_mass = DEFAULT_DISK_MASS
        state.draft_bulge_mass = DEFAULT_BULGE_MASS
        state.draft_central_mass = DEFAULT_CENTRAL_MASS
    imgui.same_line()
    apply_masses = _colored_button(
        "Appliquer",
        (button_width, 0.0),
        (
            (0.10, 0.45, 0.74, 1.00),
            (0.12, 0.56, 0.89, 1.00),
            (0.16, 0.64, 0.96, 1.00),
        ),
    )
    imgui.end_disabled()
    if not applicable:
        imgui.text_disabled("Ces masses ne s'appliquent pas à ce scénario.")
    elif not preview:
        imgui.text_disabled("Arrête la simulation pour modifier les masses.")
    if not apply_masses or not preview or not applicable:
        return None
    return ExperimentConfig(
        scenario=state.draft_scenario,
        particle_count=state.draft_particle_count,
        seed=state.draft_seed,
        disk_mass=state.draft_disk_mass,
        bulge_mass=state.draft_bulge_mass,
        central_mass=state.draft_central_mass,
    )


def _draw_data_drawer(
    state: UiState,
    stats: FrameStats,
    *,
    simulation: SimulationStatus,
    observations: ParticleObservations | None,
    graphics: GraphicsInfo,
    window_size: tuple[int, int],
    panel_width: float,
    dpi_scale: float,
    dock_top_y: float,
) -> tuple[SolverMode | None, ExperimentConfig | None]:
    if state.data_drawer is DataDrawer.NONE:
        return None, None
    width, height = window_size
    drawer_width = panel_width - 24.0 * dpi_scale
    drawer_height = min(286.0 * dpi_scale, height - 84.0 * dpi_scale)
    drawer_x = width - panel_width + 12.0 * dpi_scale
    drawer_y = max(12.0 * dpi_scale, dock_top_y - drawer_height - 8.0 * dpi_scale)
    imgui.set_next_window_pos((drawer_x, drawer_y), imgui.Cond_.always)
    imgui.set_next_window_size((drawer_width, drawer_height), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.995)
    flags = _panel_flags() | imgui.WindowFlags_.no_title_bar
    expanded, _ = imgui.begin("Gravity##data-drawer", None, flags)
    selected_solver = None
    selected_experiment = None
    if expanded:
        titles = {
            DataDrawer.MASSES: "Masses de la galaxie",
            DataDrawer.STATISTICS: strings.PHYSICAL_STATS,
            DataDrawer.PERFORMANCE: strings.PERFORMANCE,
            DataDrawer.TECHNICAL: "Technique et commandes",
        }
        eyebrow = (
            "RÉGLAGES AVANCÉS" if state.data_drawer is DataDrawer.MASSES else "DONNÉES EN DIRECT"
        )
        imgui.text_colored((0.39, 0.75, 1.00, 1.00), eyebrow)
        imgui.text(titles[state.data_drawer])
        imgui.same_line()
        close_width = 30.0 * dpi_scale
        imgui.set_cursor_pos_x(max(imgui.get_cursor_pos_x(), drawer_width - 44.0 * dpi_scale))
        if imgui.button("×##close-drawer", (close_width, 0.0)):
            state.data_drawer = DataDrawer.NONE
        imgui.separator()
        if state.data_drawer is DataDrawer.MASSES:
            selected_experiment = _draw_mass_drawer(state, simulation)
        elif state.data_drawer is DataDrawer.STATISTICS:
            _draw_statistics_drawer(observations)
        elif state.data_drawer is DataDrawer.PERFORMANCE:
            _draw_performance_drawer(stats, simulation)
        elif state.data_drawer is DataDrawer.TECHNICAL:
            selected_solver = _draw_technical_drawer(simulation, graphics)
    imgui.end()
    return selected_solver, selected_experiment


def draw_control_panel(
    state: UiState,
    stats: FrameStats,
    *,
    simulation: SimulationStatus,
    graphics: GraphicsInfo,
    window_size: tuple[int, int],
    dpi_scale: float,
    observations: ParticleObservations | None = None,
) -> UiActions:
    """Draw the right panel and return discrete requests for the app controller."""

    _synchronize_experiment_draft(state, simulation)
    if not state.panel_visible:
        return UiActions()

    width, height = window_size
    panel_width = min(max(390.0 * dpi_scale, 340.0), max(340.0, width * 0.44))
    imgui.set_next_window_pos((width - panel_width, 0.0), imgui.Cond_.always)
    imgui.set_next_window_size((panel_width, float(height)), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.975)

    expanded, _ = imgui.begin("Gravity##control-panel", None, _panel_flags())
    selected_experiment = None
    start_simulation = False
    stop_simulation = False
    toggle_pause = False
    reset_camera = False
    selected_time_scale = None
    selected_camera_view = None
    dock_top_y = float(height) - 48.0 * dpi_scale
    if expanded:
        dock_height = 36.0 * dpi_scale
        content_height = max(1.0, imgui.get_content_region_avail().y - dock_height)
        child_flags = imgui.WindowFlags_.no_scrollbar | imgui.WindowFlags_.no_scroll_with_mouse
        child_open = imgui.begin_child(
            "##primary-controls",
            (0.0, content_height),
            imgui.ChildFlags_.none,
            child_flags,
        )
        if child_open:
            _draw_header(simulation)
            selected_experiment, start_simulation = _draw_experiment(
                state,
                simulation,
                compact=height < 880.0 * dpi_scale,
            )
            (
                stop_simulation,
                toggle_pause,
                reset_camera,
                selected_time_scale,
            ) = _draw_transport(state, simulation)
            selected_camera_view = _draw_observation(
                state,
                simulation,
                observations,
                dpi_scale,
            )
        imgui.end_child()
        dock_top_y = _draw_data_dock(state)
    imgui.end()

    selected_solver, mass_experiment = _draw_data_drawer(
        state,
        stats,
        simulation=simulation,
        observations=observations,
        graphics=graphics,
        window_size=window_size,
        panel_width=panel_width,
        dpi_scale=dpi_scale,
        dock_top_y=dock_top_y,
    )
    return UiActions(
        reset_camera=reset_camera,
        start_simulation=start_simulation,
        stop_simulation=stop_simulation,
        toggle_pause=toggle_pause,
        time_scale=selected_time_scale,
        solver_mode=selected_solver,
        experiment=mass_experiment if mass_experiment is not None else selected_experiment,
        camera_view=selected_camera_view,
    )


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
        imgui.text_disabled(strings.KEYBOARD_HELP)
    imgui.end()
