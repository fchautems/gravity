"""Dear ImGui control panel and compact performance overlay."""

from __future__ import annotations

from dataclasses import dataclass

from imgui_bundle import imgui

from gravity.app.animation import AnimationClock
from gravity.diagnostics.frame_stats import FrameStats
from gravity.rendering.particles import GraphicsInfo
from gravity.ui import strings


@dataclass(slots=True)
class UiState:
    panel_visible: bool = True
    point_scale: float = 1.0


@dataclass(frozen=True, slots=True)
class UiActions:
    reset_camera: bool = False
    restart_animation: bool = False


def _panel_flags() -> imgui.WindowFlags:
    return (
        imgui.WindowFlags_.no_move
        | imgui.WindowFlags_.no_resize
        | imgui.WindowFlags_.no_collapse
        | imgui.WindowFlags_.no_saved_settings
    )


def draw_control_panel(
    state: UiState,
    clock: AnimationClock,
    stats: FrameStats,
    *,
    particle_count: int,
    graphics: GraphicsInfo,
    window_size: tuple[int, int],
    dpi_scale: float,
) -> UiActions:
    """Draw the right panel and return discrete requests for the app controller."""

    if not state.panel_visible:
        return _draw_settings_toggle(state, window_size, dpi_scale)

    width, height = window_size
    panel_width = min(max(315.0 * dpi_scale, 300.0), max(300.0, width * 0.44))
    imgui.set_next_window_pos((width - panel_width, 0.0), imgui.Cond_.always)
    imgui.set_next_window_size((panel_width, float(height)), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.96)

    expanded, _ = imgui.begin("Gravity##control-panel", None, _panel_flags())
    reset_camera = False
    restart_animation = False
    if expanded:
        imgui.text_colored((0.30, 0.72, 1.00, 1.00), strings.APP_NAME)
        imgui.text(strings.SCENE_NAME)
        imgui.text_disabled(strings.VISUAL_MILESTONE)
        imgui.spacing()
        imgui.text_wrapped(strings.SYNTHETIC_NOTICE)

        imgui.separator_text(strings.CONTROLS)
        if imgui.button(strings.RESUME if clock.paused else strings.PAUSE, (-1.0, 0.0)):
            clock.toggle_pause()
        if imgui.button(strings.RESTART, (-1.0, 0.0)):
            restart_animation = True
        if imgui.button(strings.RESET_CAMERA, (-1.0, 0.0)):
            reset_camera = True

        _, state.point_scale = imgui.slider_float(
            strings.POINT_SIZE,
            state.point_scale,
            0.55,
            2.4,
            "%.2f×",
        )
        _, clock.speed = imgui.slider_float(
            strings.ANIMATION_SPEED,
            clock.speed,
            0.0,
            2.5,
            "%.2f×",
        )

        imgui.separator_text(strings.PERFORMANCE)
        imgui.text(f"{stats.fps:5.1f} FPS")
        imgui.text_disabled(f"Image médiane : {stats.frame_ms:5.2f} ms")
        imgui.text_disabled(f"Rendu médian : {stats.draw_ms:5.2f} ms")
        imgui.text(f"{particle_count:,} particules".replace(",", "’"))
        imgui.text_disabled("1 tampon GPU · 1 appel de dessin")

        if imgui.collapsing_header(strings.GRAPHICS):
            imgui.text_wrapped(graphics.renderer)
            imgui.text_disabled(f"OpenGL {graphics.version_code / 100:.1f} · {graphics.vendor}")

        if imgui.collapsing_header(strings.HELP):
            imgui.text_wrapped(strings.MOUSE_HELP)

        imgui.spacing()
        if imgui.button(strings.HIDE_SETTINGS, (-1.0, 0.0)):
            state.panel_visible = False
    imgui.end()
    return UiActions(reset_camera=reset_camera, restart_animation=restart_animation)


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
