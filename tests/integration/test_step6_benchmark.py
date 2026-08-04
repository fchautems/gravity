from __future__ import annotations

import json
from pathlib import Path

from benchmarks.step6_barnes_hut import run_benchmark

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_step6_benchmark_emits_machine_readable_accuracy_and_timings() -> None:
    payload = run_benchmark((100,), repeats=1, direct_limit=100)
    assert payload["benchmark"] == "gravity-step6-barnes-hut"
    assert payload["configuration"]["theta"] == 0.7
    point = payload["points"][0]
    assert point["particle_count"] == 100
    assert point["node_count"] >= point["leaf_count"] > 0
    assert point["tree_build_median_ms"] >= 0.0
    assert point["force_median_ms"] >= 0.0
    assert point["exact_median_ms"] >= 0.0
    assert point["median_relative_error"] <= 0.02
    assert point["percentile_95_relative_error"] <= 0.05


def test_committed_baseline_records_the_step6_gate() -> None:
    baseline_path = PROJECT_ROOT / "benchmarks" / "results" / "step6_linux_x86_64.json"
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    points = {point["particle_count"]: point for point in payload["points"]}
    default = points[10_000]
    assert default["speedup_over_exact"] >= 10.0
    assert default["median_relative_error"] <= 0.02
    assert default["percentile_95_relative_error"] <= 0.05
    assert points[50_000]["tree_megabytes"] < 10.0
