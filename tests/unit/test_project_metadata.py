from __future__ import annotations

import tomllib
from pathlib import Path

from gravity import __version__

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_package_and_project_versions_match() -> None:
    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == __version__
    assert metadata["project"]["requires-python"] == ">=3.12,<3.13"


def test_runtime_lock_contains_the_accepted_numeric_and_graphics_versions() -> None:
    lock = (PROJECT_ROOT / "requirements" / "step5.lock").read_text(encoding="utf-8")
    assert "numpy==2.4.6" in lock
    assert "numba==0.66.0" in lock
    assert "llvmlite==0.48.0" in lock
    assert "moderngl==5.12.0" in lock
    assert "glfw==2.10.2" in lock
    assert "imgui-bundle==1.92.801" in lock
    assert "PyOpenGL==3.1.10" in lock
