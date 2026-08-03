"""Non-graphical startup checks for the pinned step-2 runtime."""

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
    "llvmlite": "0.48.0",
    "numba": "0.66.0",
    "numpy": "2.4.6",
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


def run_runtime_checks(*, run_jit: bool = True) -> CompatibilityReport:
    """Validate Python, architecture, pinned numeric packages, and Numba JIT."""

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
    if run_jit:
        checks.append(_run_numba_smoke())

    environment = {
        "machine": platform.machine() or "inconnue",
        "operating_system": platform.system() or "inconnu",
        "python": python_version,
        "python_implementation": implementation,
    }
    return CompatibilityReport(tuple(checks), environment)
