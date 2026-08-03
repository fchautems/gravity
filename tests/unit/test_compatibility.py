from __future__ import annotations

import json
from pathlib import Path

from gravity.diagnostics.compatibility import EXPECTED_PACKAGES, run_runtime_checks


def test_pinned_runtime_is_compatible(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setenv("GRAVITY_DATA_DIR", str(tmp_path))  # type: ignore[attr-defined]
    report = run_runtime_checks(run_jit=False)
    assert report.ok, report.to_lines()
    assert set(EXPECTED_PACKAGES) == {"llvmlite", "numba", "numpy"}


def test_report_json_is_machine_readable(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setenv("GRAVITY_DATA_DIR", str(tmp_path))  # type: ignore[attr-defined]
    report = run_runtime_checks(run_jit=False)
    payload = json.loads(report.to_json())
    assert payload["ok"] is True
    assert payload["environment"]["python_implementation"] == "CPython"
    assert all({"name", "ok", "detail"} == set(check) for check in payload["checks"])
