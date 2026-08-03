from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from gravity.app import bootstrap
from gravity.app.bootstrap import (
    EXIT_APPLICATION_ERROR,
    EXIT_INCOMPATIBLE_RUNTIME,
    EXIT_SUCCESS,
    EXIT_UNEXPECTED_ERROR,
    main,
)
from gravity.core.errors import ApplicationStartupError
from gravity.diagnostics.compatibility import CheckResult, CompatibilityReport


def test_diagnostic_cli_returns_json(
    monkeypatch: object,
    tmp_path: Path,
    capsys: object,
) -> None:
    monkeypatch.setenv("GRAVITY_DATA_DIR", str(tmp_path))  # type: ignore[attr-defined]
    result = main(["--diagnostic", "--json", "--skip-jit"])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert result == EXIT_SUCCESS
    assert json.loads(captured.out)["ok"] is True


def test_module_entrypoint_runs_from_an_arbitrary_working_directory(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["GRAVITY_DATA_DIR"] = str(tmp_path / "user data")
    completed = subprocess.run(
        [sys.executable, "-m", "gravity", "--diagnostic", "--json", "--skip-jit"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["ok"] is True


def test_normal_launch_hands_over_to_the_graphics_application(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GRAVITY_DATA_DIR", str(tmp_path))  # type: ignore[attr-defined]
    launches: list[bool] = []
    monkeypatch.setattr(  # type: ignore[attr-defined]
        bootstrap,
        "_run_application",
        lambda _logger: launches.append(True),
    )
    result = main(["--no-dialog", "--skip-jit"])
    assert result == EXIT_SUCCESS
    assert launches == [True]


def test_incompatible_runtime_returns_a_distinct_exit_code(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GRAVITY_DATA_DIR", str(tmp_path))  # type: ignore[attr-defined]
    report = CompatibilityReport(
        checks=(CheckResult("Python", False, "version incorrecte"),),
        environment={},
    )
    monkeypatch.setattr(bootstrap, "run_runtime_checks", lambda **_: report)  # type: ignore[attr-defined]
    assert main(["--no-dialog", "--skip-jit"]) == EXIT_INCOMPATIBLE_RUNTIME


def test_unexpected_startup_error_is_caught_at_the_application_boundary(
    monkeypatch: object,
    tmp_path: Path,
    capsys: object,
) -> None:
    monkeypatch.setenv("GRAVITY_DATA_DIR", str(tmp_path))  # type: ignore[attr-defined]

    def fail(**_: object) -> CompatibilityReport:
        raise RuntimeError("test failure")

    monkeypatch.setattr(bootstrap, "run_runtime_checks", fail)  # type: ignore[attr-defined]
    result = main(["--no-dialog", "--skip-jit"])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert result == EXIT_UNEXPECTED_ERROR
    assert "erreur inattendue" in captured.err


def test_expected_graphics_error_has_an_actionable_message(
    monkeypatch: object,
    tmp_path: Path,
    capsys: object,
) -> None:
    monkeypatch.setenv("GRAVITY_DATA_DIR", str(tmp_path))  # type: ignore[attr-defined]

    def fail(_logger: object) -> None:
        raise ApplicationStartupError("Pilote OpenGL incompatible.")

    monkeypatch.setattr(bootstrap, "_run_application", fail)  # type: ignore[attr-defined]
    result = main(["--no-dialog", "--skip-jit"])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert result == EXIT_APPLICATION_ERROR
    assert "fenetre 3D" in captured.err
    assert "Pilote OpenGL incompatible" in captured.err
