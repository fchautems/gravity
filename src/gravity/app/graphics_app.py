"""Composition root for the step-3 interactive graphics shell."""

from __future__ import annotations

import logging
from collections.abc import Callable
from time import perf_counter

import moderngl
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer

from gravity.app.animation import AnimationClock
from gravity.diagnostics.frame_stats import FrameStats
from gravity.rendering.camera import OrbitCamera
from gravity.rendering.glfw_input import GlfwInputRouter
from gravity.rendering.particles import ParticleRenderer
from gravity.rendering.window import GlfwWindow, GraphicsInitializationError
from gravity.scenarios.synthetic import generate_synthetic_galaxy
from gravity.ui.panel import UiState, draw_control_panel, draw_performance_overlay
from gravity.ui.theme import configure_theme


def _release_safely(logger: logging.Logger, label: str, release: Callable[[], None]) -> None:
    try:
        release()
    except Exception:  # noqa: BLE001 - best-effort cleanup must continue
        logger.exception("Failed to release %s", label)


def run_graphics_app(logger: logging.Logger) -> None:
    """Open the window and run until the user closes it."""

    window = GlfwWindow(logger)
    context = None
    imgui_renderer = None
    particle_renderer = None
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

        field = generate_synthetic_galaxy()
        particle_renderer = ParticleRenderer(context, field)
        graphics_info = particle_renderer.graphics_info()
        logger.info(
            "Graphics ready: OpenGL %s, renderer=%s, vendor=%s, particles=%s",
            graphics_info.version,
            graphics_info.renderer,
            graphics_info.vendor,
            field.count,
        )

        ui_state = UiState()
        clock = AnimationClock()
        stats = FrameStats()
        previous_frame_start = perf_counter()

        while not window.should_close():
            frame_start = perf_counter()
            frame_seconds = frame_start - previous_frame_start
            previous_frame_start = frame_start

            window.poll_events()
            imgui_renderer.process_inputs()  # type: ignore[no-untyped-call]
            imgui.new_frame()

            window_size = window.window_size()
            framebuffer_width, framebuffer_height = window.framebuffer_size()
            input_router.update_camera(
                ui_captures_mouse=bool(imgui.get_io().want_capture_mouse),
                viewport_height=window_size[1],
            )
            clock.advance(frame_seconds)

            actions = draw_control_panel(
                ui_state,
                clock,
                stats,
                particle_count=field.count,
                graphics=graphics_info,
                window_size=window_size,
                dpi_scale=dpi_scale,
            )
            draw_performance_overlay(stats)
            if actions.reset_camera:
                camera.reset()
            if actions.restart_animation:
                clock.restart()

            draw_start = perf_counter()
            particle_renderer.render(
                camera,
                framebuffer_width=framebuffer_width,
                framebuffer_height=framebuffer_height,
                animation_time=clock.elapsed,
                point_scale=ui_state.point_scale,
            )
            imgui.render()
            imgui_renderer.render(imgui.get_draw_data())
            window.swap_buffers()
            draw_seconds = perf_counter() - draw_start
            stats.record(perf_counter() - frame_start, draw_seconds)

        logger.info("Graphics window closed normally")
    finally:
        if particle_renderer is not None:
            _release_safely(logger, "particle renderer", particle_renderer.release)
        if imgui_renderer is not None:
            _release_safely(logger, "ImGui renderer", imgui_renderer.shutdown)
        if imgui_context_created:
            _release_safely(logger, "ImGui context", imgui.destroy_context)
        if context is not None:
            _release_safely(logger, "ModernGL context", context.release)
        _release_safely(logger, "GLFW window", window.close)
