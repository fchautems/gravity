from __future__ import annotations

from pathlib import Path

from gravity.diagnostics.compatibility import run_runtime_checks


def test_numba_compiles_and_executes(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setenv("GRAVITY_DATA_DIR", str(tmp_path))  # type: ignore[attr-defined]
    monkeypatch.setenv("NUMBA_CACHE_DIR", str(tmp_path / "numba"))  # type: ignore[attr-defined]
    report = run_runtime_checks(run_jit=True)
    numba_check = next(check for check in report.checks if check.name == "Compilation Numba")
    assert numba_check.ok, numba_check.detail
