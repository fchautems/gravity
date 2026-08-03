from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _batch(name: str) -> str:
    content = (PROJECT_ROOT / name).read_text(encoding="utf-8")
    assert content.isascii(), f"{name} must remain independent from cmd.exe code pages"
    return content


def test_all_launchers_anchor_paths_to_their_own_directory() -> None:
    for name in ("INSTALLER.bat", "LANCER_GRAVITY.bat", "TESTER_GRAVITY.bat"):
        content = _batch(name)
        assert 'pushd "%~dp0"' in content


def test_installer_requires_python_312_64_bit() -> None:
    content = _batch("INSTALLER.bat")
    assert "py -3.12-64" in content
    assert "struct.calcsize('P') * 8 == 64" in content
    assert '"%~dp0tools\\bootstrap.py" install' in content


def test_normal_launcher_uses_pythonw_without_a_persistent_console() -> None:
    content = _batch("LANCER_GRAVITY.bat")
    assert ".venv\\Scripts\\pythonw.exe" in content
    assert 'start "" /B "%GRAVITY_PYTHONW%" -m gravity' in content
    assert "message.vbs" in content


def test_test_launcher_uses_the_isolated_environment() -> None:
    content = _batch("TESTER_GRAVITY.bat")
    assert ".venv\\Scripts\\python.exe" in content
    assert '"%~dp0tools\\bootstrap.py" test' in content
