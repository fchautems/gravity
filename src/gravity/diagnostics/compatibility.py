"""Non-graphical startup checks for the pinned numerical and graphics runtime."""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import struct
import sys
from dataclasses import asdict, dataclass
from typing import Any

from gravity.core.paths import ensure_user_directories

SUPPORTED_PYTHON = (3, 12)
EXPECTED_PACKAGES = {
    "glcontext": "3.0.0",
    "glfw": "2.10.2",
    "imgui-bundle": "1.92.801",
    "llvmlite": "0.48.0",
    "moderngl": "5.12.0",
    "numba": "0.66.0",
    "numpy": "2.4.6",
    "PyOpenGL": "3.1.10",
    "PyOpenGL-accelerate": "3.1.10",
}


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One compatibility assertion and its user-readable detail."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    """Complete result of the non-graphical startup diagnostics."""

    checks: tuple[CheckResult, ...]
    environment: dict[str, str]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [asdict(check) for check in self.checks],
            "environment": self.environment,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)

    def to_lines(self) -> list[str]:
        lines = []
        for check in self.checks:
            marker = "OK" if check.ok else "ECHEC"
            lines.append(f"[{marker}] {check.name}: {check.detail}")
        return lines


def _package_check(distribution: str, expected: str) -> CheckResult:
    try:
        installed = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return CheckResult(distribution, False, "paquet absent")
    return CheckResult(
        distribution,
        installed == expected,
        f"version {installed} (attendue: {expected})",
    )


def _run_numba_smoke() -> CheckResult:
    try:
        directories = ensure_user_directories()
        numba_cache = directories.cache / "numba"
        numba_cache.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("NUMBA_CACHE_DIR", str(numba_cache))

        import numpy as np

        from gravity.diagnostics.jit_smoke import weighted_checksum

        values = np.array([0.5, 1.5, -2.0, 4.0], dtype=np.float64)
        actual = float(weighted_checksum(values))
        expected = 13.5
        if actual != expected:
            return CheckResult(
                "Compilation Numba",
                False,
                f"resultat {actual} au lieu de {expected}",
            )
    except Exception as error:  # noqa: BLE001 - diagnostic boundary by design
        return CheckResult(
            "Compilation Numba",
            False,
            f"{type(error).__name__}: {error}",
        )
    return CheckResult("Compilation Numba", True, "calcul natif valide")


def _run_barnes_hut_smoke() -> CheckResult:
    """Warm and verify the real sequential and parallel step-6 kernels."""

    try:
        import numpy as np

        from gravity.physics import BarnesHutSolver

        particle_count = 2_100
        phase = np.linspace(0.0, 12.0 * np.pi, particle_count, endpoint=False)
        radius = np.linspace(0.2, 6.0, particle_count)
        positions = np.ascontiguousarray(
            np.column_stack(
                (
                    radius * np.cos(phase),
                    0.05 * np.sin(phase * 0.37),
                    radius * np.sin(phase),
                )
            ),
            dtype=np.float64,
        )
        masses = np.full(particle_count, 1.0 / particle_count, dtype=np.float64)
        solver = BarnesHutSolver()
        acceleration = solver.compute(positions, masses, 0.08)
        stats = solver.last_stats
        if (
            stats is None
            or stats.particle_count != particle_count
            or stats.node_count < 2
            or not np.all(np.isfinite(acceleration))
        ):
            return CheckResult(
                "Moteur Barnes-Hut",
                False,
                "arbre, statistiques ou accelerations invalides",
            )
    except Exception as error:  # noqa: BLE001 - diagnostic boundary by design
        return CheckResult(
            "Moteur Barnes-Hut",
            False,
            f"{type(error).__name__}: {error}",
        )
    return CheckResult(
        "Moteur Barnes-Hut",
        True,
        "octree et parcours parallele natifs valides",
    )


def _run_graphics_import_smoke() -> CheckResult:
    """Import the complete graphics integration without opening a display."""

    try:
        import glfw  # noqa: F401
        import moderngl  # noqa: F401
        import OpenGL.GL  # noqa: F401
        from imgui_bundle import imgui  # noqa: F401
        from imgui_bundle.python_backends.glfw_backend import GlfwRenderer  # noqa: F401
    except Exception as error:  # noqa: BLE001 - diagnostic boundary by design
        return CheckResult(
            "Pile graphique",
            False,
            f"{type(error).__name__}: {error}",
        )
    return CheckResult("Pile graphique", True, "imports GLFW / ModernGL / ImGui valides")


def run_runtime_checks(*, run_jit: bool = True) -> CompatibilityReport:
    """Validate Python, architecture, pinned packages, graphics imports, and JIT."""

    python_version = platform.python_version()
    python_ok = sys.version_info[:2] == SUPPORTED_PYTHON
    implementation = platform.python_implementation()
    bitness = struct.calcsize("P") * 8

    checks = [
        CheckResult(
            "Python",
            python_ok and implementation == "CPython",
            f"{implementation} {python_version} (attendu: CPython 3.12.x)",
        ),
        CheckResult(
            "Architecture",
            bitness == 64,
            f"{bitness} bits (attendu: 64 bits)",
        ),
    ]
    checks.extend(_package_check(name, version) for name, version in EXPECTED_PACKAGES.items())
    checks.append(_run_graphics_import_smoke())
    if run_jit:
        checks.append(_run_numba_smoke())
        checks.append(_run_barnes_hut_smoke())

    environment = {
        "machine": platform.machine() or "inconnue",
        "operating_system": platform.system() or "inconnu",
        "python": python_version,
        "python_implementation": implementation,
    }
    return CompatibilityReport(tuple(checks), environment)
