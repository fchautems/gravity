from __future__ import annotations

import pytest

from gravity.diagnostics.frame_stats import FrameStats


def test_frame_stats_use_rolling_medians() -> None:
    stats = FrameStats(sample_count=3)
    stats.record(0.010, 0.002)
    stats.record(0.020, 0.004)
    stats.record(0.030, 0.006)
    assert stats.fps == pytest.approx(50.0)
    assert stats.frame_ms == pytest.approx(20.0)
    assert stats.draw_ms == pytest.approx(4.0)
    stats.record(0.040, 0.008)
    assert stats.frame_ms == pytest.approx(30.0)


def test_frame_stats_ignore_invalid_samples() -> None:
    stats = FrameStats()
    stats.record(0.0, -1.0)
    assert stats.fps == 0.0
    assert stats.draw_ms == 0.0
    with pytest.raises(ValueError):
        FrameStats(sample_count=0)
