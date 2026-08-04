"""Reproducible step-6 accuracy and timing benchmark."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numba
import numpy as np

from gravity.diagnostics import compare_accelerations
from gravity.physics import BarnesHutSolver, ExactGravitySolver
from gravity.scenarios import GalaxyConfig, generate_spiral_galaxy


@dataclass(frozen=True, slots=True)
class BenchmarkPoint:
    particle_count: int
    node_count: int
    leaf_count: int
    tree_megabytes: float
    tree_build_median_ms: float
    tree_build_p95_ms: float
    force_median_ms: float
    force_p95_ms: float
    total_median_ms: float
    total_p95_ms: float
    exact_median_ms: float | None
    speedup_over_exact: float | None
    median_relative_error: float | None
    percentile_95_relative_error: float | None
    accepted_nodes_per_particle: float
    direct_particles_per_particle: float


def _percentile_95(values: list[float]) -> float:
    return float(np.quantile(np.asarray(values, dtype=np.float64), 0.95))


def _milliseconds(seconds: float) -> float:
    return 1_000.0 * seconds


def _tree_bytes(solver: BarnesHutSolver, positions: np.ndarray, masses: np.ndarray) -> int:
    tree = solver.build_tree(positions, masses)
    return sum(
        array.nbytes
        for array in (
            tree.centers,
            tree.half_sizes,
            tree.children,
            tree.starts,
            tree.counts,
            tree.depths,
            tree.masses,
            tree.centers_of_mass,
            tree.particle_order,
            tree.inverse_order,
        )
    )


def _warm_up(parallel: bool) -> None:
    count = 2_100 if parallel else 100
    galaxy = generate_spiral_galaxy(GalaxyConfig(particle_count=count, seed=101))
    BarnesHutSolver().compute(
        galaxy.state.positions,
        galaxy.state.masses,
        galaxy.config.softening,
    )
    if not parallel:
        ExactGravitySolver().compute(
            galaxy.state.positions,
            galaxy.state.masses,
            galaxy.config.softening,
        )


def benchmark_point(
    particle_count: int,
    *,
    repeats: int,
    direct_limit: int,
) -> BenchmarkPoint:
    galaxy = generate_spiral_galaxy(GalaxyConfig(particle_count=particle_count, seed=20_260_806))
    positions = galaxy.state.positions
    masses = galaxy.state.masses
    softening = galaxy.config.softening
    solver = BarnesHutSolver()
    approximate = solver.compute(positions, masses, softening)

    build_times: list[float] = []
    force_times: list[float] = []
    wall_times: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        solver.compute(positions, masses, softening)
        wall_times.append(time.perf_counter() - started)
        stats = solver.last_stats
        if stats is None:
            raise RuntimeError("Barnes-Hut statistics were not produced")
        build_times.append(stats.tree_build_seconds)
        force_times.append(stats.force_seconds)

    exact_times: list[float] = []
    exact: np.ndarray | None = None
    if particle_count <= direct_limit:
        exact_solver = ExactGravitySolver()
        exact = exact_solver.compute(positions, masses, softening)
        for _ in range(repeats):
            started = time.perf_counter()
            exact_solver.compute(positions, masses, softening)
            exact_times.append(time.perf_counter() - started)

    stats = solver.last_stats
    if stats is None:
        raise RuntimeError("Barnes-Hut statistics were not produced")
    error = compare_accelerations(exact, approximate) if exact is not None else None
    total_median = statistics.median(wall_times)
    exact_median = statistics.median(exact_times) if exact_times else None
    return BenchmarkPoint(
        particle_count=particle_count,
        node_count=stats.node_count,
        leaf_count=stats.leaf_count,
        tree_megabytes=_tree_bytes(solver, positions, masses) / (1024.0 * 1024.0),
        tree_build_median_ms=_milliseconds(statistics.median(build_times)),
        tree_build_p95_ms=_milliseconds(_percentile_95(build_times)),
        force_median_ms=_milliseconds(statistics.median(force_times)),
        force_p95_ms=_milliseconds(_percentile_95(force_times)),
        total_median_ms=_milliseconds(total_median),
        total_p95_ms=_milliseconds(_percentile_95(wall_times)),
        exact_median_ms=_milliseconds(exact_median) if exact_median is not None else None,
        speedup_over_exact=exact_median / total_median if exact_median is not None else None,
        median_relative_error=error.median_relative_error if error is not None else None,
        percentile_95_relative_error=(
            error.percentile_95_relative_error if error is not None else None
        ),
        accepted_nodes_per_particle=(stats.accepted_node_interactions / particle_count),
        direct_particles_per_particle=(stats.direct_particle_interactions / particle_count),
    )


def run_benchmark(
    particle_counts: Sequence[int],
    *,
    repeats: int,
    direct_limit: int,
) -> dict[str, Any]:
    if repeats < 1:
        raise ValueError("repeats must be strictly positive")
    if direct_limit < 0:
        raise ValueError("direct_limit must be non-negative")
    counts = tuple(int(count) for count in particle_counts)
    if not counts or any(count < 100 or count > 50_000 for count in counts):
        raise ValueError("particle counts must lie between 100 and 50,000")

    _warm_up(parallel=False)
    if any(count >= 2_048 for count in counts):
        _warm_up(parallel=True)
    points = [
        benchmark_point(count, repeats=repeats, direct_limit=direct_limit) for count in counts
    ]
    return {
        "benchmark": "gravity-step6-barnes-hut",
        "configuration": {
            "seed": 20_260_806,
            "theta": 0.7,
            "leaf_capacity": 8,
            "depth_limit": 32,
            "repeats": repeats,
            "direct_limit": direct_limit,
        },
        "environment": {
            "machine": platform.machine(),
            "operating_system": platform.platform(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "numba": numba.__version__,
            "numba_threads": numba.get_num_threads(),
        },
        "points": [asdict(point) for point in points],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--particles", type=int, nargs="+", default=[100, 1_000, 10_000])
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--direct-limit", type=int, default=10_000)
    parser.add_argument("--json", action="store_true")
    return parser


def _human_report(payload: dict[str, Any]) -> str:
    lines = [
        "particles | tree ms | force ms | total ms | exact ms | speedup | median err | p95 err"
    ]
    for point in payload["points"]:
        exact = "-" if point["exact_median_ms"] is None else f"{point['exact_median_ms']:.3f}"
        speedup = (
            "-" if point["speedup_over_exact"] is None else f"{point['speedup_over_exact']:.2f}x"
        )
        median_error = (
            "-"
            if point["median_relative_error"] is None
            else f"{100.0 * point['median_relative_error']:.3f}%"
        )
        p95_error = (
            "-"
            if point["percentile_95_relative_error"] is None
            else f"{100.0 * point['percentile_95_relative_error']:.3f}%"
        )
        lines.append(
            f"{point['particle_count']:9d} | {point['tree_build_median_ms']:7.3f} | "
            f"{point['force_median_ms']:8.3f} | {point['total_median_ms']:8.3f} | "
            f"{exact:>8} | {speedup:>7} | {median_error:>10} | {p95_error:>8}"
        )
    return "\n".join(lines)


def main(arguments: Sequence[str] | None = None) -> int:
    options = _parser().parse_args(arguments)
    payload = run_benchmark(
        options.particles,
        repeats=options.repeats,
        direct_limit=options.direct_limit,
    )
    if options.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_human_report(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
