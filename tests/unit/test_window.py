from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from gravity.rendering.window import GlfwWindow, GraphicsInitializationError


class FakeGlfw:
    CONTEXT_VERSION_MAJOR = 1
    CONTEXT_VERSION_MINOR = 2
    OPENGL_PROFILE = 3
    OPENGL_CORE_PROFILE = 4
    OPENGL_FORWARD_COMPAT = 5
    SAMPLES = 6
    SCALE_TO_MONITOR = 7
    TRUE = 1
    DONT_CARE = -1

    def __init__(self, *, initializes: bool = True, creates_window: bool = True) -> None:
        self.initializes = initializes
        self.creates_window = creates_window
        self.handle = object()
        self.terminated = 0
        self.destroyed = 0
        self.hints: list[tuple[int, int]] = []
        self.error_callback: object | None = None
        self.monitor_changes: list[tuple[object | None, int, int, int, int, int]] = []

    def set_error_callback(self, callback: object) -> None:
        self.error_callback = callback

    def init(self) -> bool:
        return self.initializes

    def window_hint(self, key: int, value: int) -> None:
        self.hints.append((key, value))

    def create_window(self, *_args: object) -> object | None:
        return self.handle if self.creates_window else None

    def make_context_current(self, _window: object) -> None:
        pass

    def swap_interval(self, _interval: int) -> None:
        pass

    def set_window_size_limits(self, *_args: object) -> None:
        pass

    def get_window_size(self, _window: object) -> tuple[int, int]:
        return (1280, 800)

    def get_window_pos(self, _window: object) -> tuple[int, int]:
        return (40, 60)

    def get_primary_monitor(self) -> object:
        return "monitor"

    def get_video_mode(self, _monitor: object) -> object:
        return SimpleNamespace(size=(1920, 1080), refresh_rate=60)

    def set_window_monitor(
        self,
        _window: object,
        monitor: object | None,
        x: int,
        y: int,
        width: int,
        height: int,
        refresh_rate: int,
    ) -> None:
        self.monitor_changes.append((monitor, x, y, width, height, refresh_rate))

    def get_framebuffer_size(self, _window: object) -> tuple[int, int]:
        return (1920, 1200)

    def get_window_content_scale(self, _window: object) -> tuple[float, float]:
        return (1.5, 1.5)

    def window_should_close(self, _window: object) -> bool:
        return False

    def poll_events(self) -> None:
        pass

    def swap_buffers(self, _window: object) -> None:
        pass

    def destroy_window(self, _window: object) -> None:
        self.destroyed += 1

    def terminate(self) -> None:
        self.terminated += 1


def test_window_opens_with_core_profile_and_cleans_up_once() -> None:
    glfw = FakeGlfw()
    window = GlfwWindow(logging.getLogger("test"), glfw_module=glfw)
    window.open()
    assert window.window_size() == (1280, 800)
    assert window.framebuffer_size() == (1920, 1200)
    assert window.content_scale() == 1.5
    assert (glfw.CONTEXT_VERSION_MAJOR, 3) in glfw.hints
    assert (glfw.CONTEXT_VERSION_MINOR, 3) in glfw.hints
    window.close()
    window.close()
    assert glfw.destroyed == 1
    assert glfw.terminated == 1


@pytest.mark.parametrize(
    ("initializes", "creates_window"),
    [(False, True), (True, False)],
)
def test_window_reports_initialization_failures(
    initializes: bool,
    creates_window: bool,
) -> None:
    glfw = FakeGlfw(initializes=initializes, creates_window=creates_window)
    window = GlfwWindow(logging.getLogger("test"), glfw_module=glfw)
    with pytest.raises(GraphicsInitializationError):
        window.open()
    if initializes:
        assert glfw.terminated == 1


def test_error_callback_decodes_native_byte_messages(caplog: object) -> None:
    glfw = FakeGlfw()
    window = GlfwWindow(logging.getLogger("gravity.window-test"), glfw_module=glfw)
    window.open()
    callback = glfw.error_callback
    assert callable(callback)
    with caplog.at_level(logging.WARNING):  # type: ignore[attr-defined]
        callback(42, b"driver failure")
    assert "driver failure" in caplog.text  # type: ignore[attr-defined]
    window.close()


def test_fullscreen_restores_the_previous_window_geometry() -> None:
    glfw = FakeGlfw()
    window = GlfwWindow(logging.getLogger("fullscreen-test"), glfw_module=glfw)
    window.open()
    window.toggle_fullscreen()
    assert window.fullscreen
    assert glfw.monitor_changes[-1] == ("monitor", 0, 0, 1920, 1080, 60)
    window.leave_fullscreen()
    assert not window.fullscreen
    assert glfw.monitor_changes[-1] == (None, 40, 60, 1280, 800, glfw.DONT_CARE)
    window.close()
