from __future__ import annotations

from pathlib import Path

from tools.bootstrap import InterpreterInfo, _is_supported, _next_backup_path, _venv_python


def test_supported_interpreter_contract() -> None:
    assert _is_supported(InterpreterInfo("cpython", 3, 12, 64))
    assert not _is_supported(InterpreterInfo("cpython", 3, 11, 64))
    assert not _is_supported(InterpreterInfo("cpython", 3, 12, 32))
    assert not _is_supported(InterpreterInfo("pypy", 3, 12, 64))


def test_virtual_environment_python_paths() -> None:
    root = Path("project") / ".venv"
    assert _venv_python(root, platform_name="win32") == root / "Scripts" / "python.exe"
    assert _venv_python(root, platform_name="linux") == root / "bin" / "python"


def test_incompatible_environment_backup_does_not_overwrite(tmp_path: Path) -> None:
    virtual_environment = tmp_path / ".venv"
    first = tmp_path / ".venv-incompatible-20260803-120000"
    first.mkdir()
    actual = _next_backup_path(virtual_environment, timestamp="20260803-120000")
    assert actual == tmp_path / ".venv-incompatible-20260803-120000-2"
