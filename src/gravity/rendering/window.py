"""GLFW window lifecycle and OpenGL 3.3 context creation settings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import glfw

from gravity.core.errors import ApplicationStartupError


class GraphicsInitializationError(ApplicationStartupError):
    """Raised when GLFW cannot provide Gravity's required graphics context."""


@dataclass(frozen=True, slots=True)
class WindowConfig:
    width: int = 1280
    height: int = 800
    title: str = "Gravity — Galaxie 3D"


class GlfwWindow:
    """Small owner wrapper that guarantees orderly GLFW cleanup."""

    def __init__(
        self,
        logger: logging.Logger,
        config: WindowConfig | None = None,
        *,
        glfw_module: Any = glfw,
    ) -> None:
        self._logger = logger
        self._config = config or WindowConfig()
        self._glfw = glfw_module
        self.handle: Any | None = None
        self._initialized = False
        self._fullscreen = False
        self._windowed_geometry = (100, 100, self._config.width, self._config.height)

    def open(self) -> None:
        self._glfw.set_error_callback(self._on_error)
        if not self._glfw.init():
            raise GraphicsInitializationError(
                "GLFW n'a pas pu initialiser l'affichage. Verifiez le pilote graphique."
            )
        self._initialized = True

        self._glfw.window_hint(self._glfw.CONTEXT_VERSION_MAJOR, 3)
        self._glfw.window_hint(self._glfw.CONTEXT_VERSION_MINOR, 3)
        self._glfw.window_hint(self._glfw.OPENGL_PROFILE, self._glfw.OPENGL_CORE_PROFILE)
        self._glfw.window_hint(self._glfw.OPENGL_FORWARD_COMPAT, self._glfw.TRUE)
        self._glfw.window_hint(self._glfw.SAMPLES, 4)
        if hasattr(self._glfw, "SCALE_TO_MONITOR"):
            self._glfw.window_hint(self._glfw.SCALE_TO_MONITOR, self._glfw.TRUE)

        self.handle = self._glfw.create_window(
            self._config.width,
            self._config.height,
            self._config.title,
            None,
            None,
        )
        if self.handle is None:
            self.close()
            raise GraphicsInitializationError(
                "Impossible de creer une fenetre OpenGL 3.3. Mettez le pilote graphique a jour."
            )

        self._glfw.make_context_current(self.handle)
        self._glfw.swap_interval(1)
        self._glfw.set_window_size_limits(
            self.handle, 900, 560, self._glfw.DONT_CARE, self._glfw.DONT_CARE
        )

    def _on_error(self, code: int, description: object) -> None:
        if isinstance(description, bytes):
            detail = description.decode("utf-8", errors="replace")
        else:
            detail = str(description)
        self._logger.warning("GLFW error %s: %s", code, detail)

    def window_size(self) -> tuple[int, int]:
        if self.handle is None:
            return (0, 0)
        width, height = self._glfw.get_window_size(self.handle)
        return int(width), int(height)

    def framebuffer_size(self) -> tuple[int, int]:
        if self.handle is None:
            return (0, 0)
        width, height = self._glfw.get_framebuffer_size(self.handle)
        return int(width), int(height)

    def content_scale(self) -> float:
        if self.handle is None or not hasattr(self._glfw, "get_window_content_scale"):
            return 1.0
        scale_x, scale_y = self._glfw.get_window_content_scale(self.handle)
        return max(1.0, min(float(max(scale_x, scale_y)), 2.0))

    def should_close(self) -> bool:
        return self.handle is None or bool(self._glfw.window_should_close(self.handle))

    def poll_events(self) -> None:
        self._glfw.poll_events()

    def swap_buffers(self) -> None:
        if self.handle is not None:
            self._glfw.swap_buffers(self.handle)

    @property
    def fullscreen(self) -> bool:
        return self._fullscreen

    def toggle_fullscreen(self) -> None:
        """Switch between borderless monitor mode and the previous window geometry."""

        if self.handle is None:
            return
        if self._fullscreen:
            x, y, width, height = self._windowed_geometry
            self._glfw.set_window_monitor(
                self.handle,
                None,
                x,
                y,
                width,
                height,
                self._glfw.DONT_CARE,
            )
            self._fullscreen = False
            return

        x, y = self._glfw.get_window_pos(self.handle)
        width, height = self._glfw.get_window_size(self.handle)
        self._windowed_geometry = (int(x), int(y), int(width), int(height))
        monitor = self._glfw.get_primary_monitor()
        if monitor is None:
            self._logger.warning("No primary monitor available for fullscreen mode")
            return
        mode = self._glfw.get_video_mode(monitor)
        if mode is None:
            self._logger.warning("No video mode available for fullscreen mode")
            return
        size = mode.size
        monitor_width = int(size.width if hasattr(size, "width") else size[0])
        monitor_height = int(size.height if hasattr(size, "height") else size[1])
        refresh_rate = int(mode.refresh_rate)
        self._glfw.set_window_monitor(
            self.handle,
            monitor,
            0,
            0,
            monitor_width,
            monitor_height,
            refresh_rate,
        )
        self._fullscreen = True

    def leave_fullscreen(self) -> None:
        if self._fullscreen:
            self.toggle_fullscreen()

    def close(self) -> None:
        if self.handle is not None:
            self._glfw.destroy_window(self.handle)
            self.handle = None
        if self._initialized:
            self._glfw.terminate()
            self._initialized = False
