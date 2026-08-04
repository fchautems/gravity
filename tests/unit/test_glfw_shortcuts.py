from __future__ import annotations

from gravity.rendering.camera import OrbitCamera
from gravity.rendering.glfw_input import GlfwInputRouter


class FakeGlfw:
    PRESS = 1
    RELEASE = 0
    KEY_SPACE = 32
    KEY_R = 82
    KEY_F = 70
    KEY_ESCAPE = 256
    KEY_TAB = 258

    def __init__(self) -> None:
        self.down: set[int] = set()

    def get_key(self, _window: object, key: int) -> int:
        return self.PRESS if key in self.down else self.RELEASE


def test_shortcuts_are_edge_triggered_and_blocked_during_text_entry() -> None:
    glfw = FakeGlfw()
    router = GlfwInputRouter(object(), object(), OrbitCamera(), glfw_module=glfw)
    glfw.down = {glfw.KEY_SPACE, glfw.KEY_F}
    first = router.poll_shortcuts(ui_captures_keyboard=False)
    assert first.toggle_pause
    assert first.toggle_fullscreen
    assert not router.poll_shortcuts(ui_captures_keyboard=False).toggle_pause

    glfw.down.clear()
    router.poll_shortcuts(ui_captures_keyboard=False)
    glfw.down = {glfw.KEY_R, glfw.KEY_TAB}
    blocked = router.poll_shortcuts(ui_captures_keyboard=True)
    assert not blocked.reset_camera
    assert not blocked.toggle_panel
