from __future__ import annotations

from types import SimpleNamespace

from gravity.app import user_feedback


def test_non_windows_feedback_uses_the_expected_streams(
    monkeypatch: object,
    capsys: object,
) -> None:
    monkeypatch.setattr(user_feedback.sys, "platform", "linux")  # type: ignore[attr-defined]
    user_feedback.show_message("Gravity", "information")
    user_feedback.show_message("Gravity", "erreur", error=True)
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "Gravity: information" in captured.out
    assert "Gravity: erreur" in captured.err


def test_windows_feedback_calls_the_native_message_box(monkeypatch: object) -> None:
    calls: list[tuple[object, str, str, int]] = []

    class FakeUser32:
        def MessageBoxW(self, owner: object, message: str, title: str, style: int) -> None:
            calls.append((owner, message, title, style))

    fake_windll = SimpleNamespace(user32=FakeUser32())
    monkeypatch.setattr(user_feedback.sys, "platform", "win32")  # type: ignore[attr-defined]
    monkeypatch.setattr(user_feedback.ctypes, "windll", fake_windll, raising=False)  # type: ignore[attr-defined]

    user_feedback.show_message("Gravity", "probleme", error=True)
    assert calls == [
        (
            None,
            "probleme",
            "Gravity",
            user_feedback.MESSAGE_BOX_OK | user_feedback.MESSAGE_BOX_ICON_ERROR,
        )
    ]
