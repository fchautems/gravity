"""Composition root for the coupled interactive simulation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from time import perf_counter

import moderngl
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer

from gravity.app.physics_worker import PhysicsWorker
from gravity.core.simulation import SimulationStatus
from gravity.diagnostics.frame_stats import FrameStats
from gravity.rendering.camera import CameraView, OrbitCamera
from gravity.rendering.glfw_input import GlfwInputRouter
from gravity.rendering.particles import (
    ParticleRenderer,
    center_marker_field,
    physical_particle_field,
)
from gravity.rendering.window import GlfwWindow, GraphicsInitializationError
from gravity.ui.panel import UiActions, UiState, draw_control_panel, draw_performance_overlay
from gravity.ui.theme import configure_theme


def _release_safely(logger: logging.Logger, label: str, release: Callable[[], None]) -> None:
    try:
        release()
    except Exception:  # noqa: BLE001 - best-effort cleanup must continue
        logger.exception("Failed to release %s", label)


def _dispatch_simulation_actions(
    worker: PhysicsWorker,
    simulation: SimulationStatus,
    actions: UiActions,
) -> None:
    """Translate UI values into thread-safe worker commands."""

    if actions.toggle_pause:
        if simulation.paused:
            worker.resume()
        else:
            worker.pause()
    if actions.reset_simulation:
        worker.reset()
    if actions.single_step:
        worker.single_step()
    if actions.time_scale is not None:
        worker.set_time_scale(actions.time_scale)
    if actions.solver_mode is not None:
        worker.set_solver(actions.solver_mode)
    if actions.experiment is not None:
        worker.set_experiment(actions.experiment)


def run_graphics_app(logger: logging.Logger) -> None:
    """Open the window and run until the user closes it."""

    window = GlfwWindow(logger)
    context = None
    imgui_renderer = None
    particle_renderer = None
    center_renderer = None
    physics_worker = PhysicsWorker(logger)
    imgui_context_created = False

    try:
        window.open()
        if window.handle is None:
            raise RuntimeError("GLFW returned no window after successful initialization")

        try:
            context = moderngl.create_context(require=330)
        except Exception as error:  # noqa: BLE001 - graphics driver boundary
            raise GraphicsInitializationError(
                "Le pilote n'a pas fourni le contexte OpenGL 3.3 requis. "
                "Mettez le pilote graphique a jour."
            ) from error
        imgui.create_context()
        imgui_context_created = True
        dpi_scale = window.content_scale()
        configure_theme(dpi_scale)
        imgui_renderer = GlfwRenderer(window.handle, attach_callbacks=False)

        camera = OrbitCamera()
        input_router = GlfwInputRouter(window.handle, imgui_renderer, camera)
        input_router.attach()

        physics_worker.start()
        current_snapshot = physics_worker.wait_for_snapshot()
        ui_state = UiState(time_scale=current_snapshot.status.time_scale)
        particle_renderer = ParticleRenderer(
            context,
            physical_particle_field(
                current_snapshot.positions,
                current_snapshot.observations,
                ui_state.color_mode,
            ),
        )
        if current_snapshot.observations is not None:
            center_renderer = ParticleRenderer(
                context,
                center_marker_field(current_snapshot.observations.stats.center_of_mass),
            )
        graphics_info = particle_renderer.graphics_info()
        logger.info(
            "Coupled simulation ready: OpenGL %s, renderer=%s, solver=%s, particles=%s",
            graphics_info.version,
            graphics_info.renderer,
            current_snapshot.status.solver_mode.value,
            current_snapshot.status.particle_count,
        )

        stats = FrameStats()
        previous_frame_start = perf_counter()
        rendered_color_mode = ui_state.color_mode

        while not window.should_close():
            frame_start = perf_counter()
            frame_seconds = frame_start - previous_frame_start
            previous_frame_start = frame_start

            physics_worker.raise_if_failed()
            newest_snapshot = physics_worker.latest_snapshot()
            if newest_snapshot is not None:
                particle_renderer.update_positions(
                    newest_snapshot.positions,
                    observations=newest_snapshot.observations,
                    color_mode=ui_state.color_mode,
                    reset_visuals=(
                        newest_snapshot.status.generation != current_snapshot.status.generation
                    ),
                )
                if center_renderer is not None and newest_snapshot.observations is not None:
                    center_renderer.update_field(
                        center_marker_field(newest_snapshot.observations.stats.center_of_mass)
                    )
                current_snapshot = newest_snapshot
                rendered_color_mode = ui_state.color_mode

            window.poll_events()
            imgui_renderer.process_inputs()  # type: ignore[no-untyped-call]
            imgui.new_frame()

            window_size = window.window_size()
            framebuffer_width, framebuffer_height = window.framebuffer_size()
            input_router.update_camera(
                ui_captures_mouse=bool(imgui.get_io().want_capture_mouse),
                viewport_height=window_size[1],
            )
            shortcuts = input_router.poll_shortcuts(
                ui_captures_keyboard=bool(imgui.get_io().want_capture_keyboard),
            )
            if shortcuts.toggle_pause:
                if current_snapshot.status.paused:
                    physics_worker.resume()
                else:
                    physics_worker.pause()
            if shortcuts.reset_camera:
                camera.reset()
                ui_state.camera_view = CameraView.PERSPECTIVE
            if shortcuts.toggle_fullscreen:
                window.toggle_fullscreen()
            if shortcuts.leave_fullscreen:
                window.leave_fullscreen()
            if shortcuts.toggle_panel:
                ui_state.panel_visible = not ui_state.panel_visible

            actions = draw_control_panel(
                ui_state,
                stats,
                simulation=current_snapshot.status,
                graphics=graphics_info,
                window_size=window_size,
                dpi_scale=dpi_scale,
                observations=current_snapshot.observations,
            )
            if ui_state.panel_visible:
                draw_performance_overlay(stats)
            if actions.reset_camera:
                camera.reset()
                ui_state.camera_view = CameraView.PERSPECTIVE
            if actions.camera_view is not None:
                camera.set_view(actions.camera_view)
            _dispatch_simulation_actions(physics_worker, current_snapshot.status, actions)

            if rendered_color_mode is not ui_state.color_mode:
                particle_renderer.update_positions(
                    current_snapshot.positions,
                    observations=current_snapshot.observations,
                    color_mode=ui_state.color_mode,
                )
                rendered_color_mode = ui_state.color_mode

            draw_start = perf_counter()
            particle_renderer.render(
                camera,
                framebuffer_width=framebuffer_width,
                framebuffer_height=framebuffer_height,
                point_scale=ui_state.point_scale,
            )
            if ui_state.show_center_of_mass and center_renderer is not None:
                center_renderer.render(
                    camera,
                    framebuffer_width=framebuffer_width,
                    framebuffer_height=framebuffer_height,
                    point_scale=1.0,
                    clear_frame=False,
                )
            imgui.render()
            imgui_renderer.render(imgui.get_draw_data())
            window.swap_buffers()
            draw_seconds = perf_counter() - draw_start
            stats.record(frame_seconds, draw_seconds)

        logger.info("Graphics window closed normally")
    finally:
        _release_safely(logger, "physics worker", physics_worker.shutdown)
        if particle_renderer is not None:
            _release_safely(logger, "particle renderer", particle_renderer.release)
        if center_renderer is not None:
            _release_safely(logger, "centre-of-mass renderer", center_renderer.release)
        if imgui_renderer is not None:
            _release_safely(logger, "ImGui renderer", imgui_renderer.shutdown)
        if imgui_context_created:
            _release_safely(logger, "ImGui context", imgui.destroy_context)
        if context is not None:
            _release_safely(logger, "ModernGL context", context.release)
        _release_safely(logger, "GLFW window", window.close)
