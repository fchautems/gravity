from __future__ import annotations

import pytest

from gravity.app.animation import AnimationClock


def test_animation_clock_pause_speed_restart_and_frame_cap() -> None:
    clock = AnimationClock(speed=2.0)
    clock.advance(1.0)
    assert clock.elapsed == pytest.approx(0.5)
    clock.toggle_pause()
    clock.advance(0.1)
    assert clock.elapsed == pytest.approx(0.5)
    clock.toggle_pause()
    clock.advance(0.1)
    assert clock.elapsed == pytest.approx(0.7)
    clock.restart()
    assert clock.elapsed == 0.0


def test_animation_clock_rejects_negative_time() -> None:
    with pytest.raises(ValueError):
        AnimationClock().advance(-0.01)
