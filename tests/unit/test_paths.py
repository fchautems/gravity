from __future__ import annotations

from pathlib import Path

from gravity.core.paths import ensure_user_directories, preferred_user_data_root


def test_explicit_data_root_has_priority(tmp_path: Path) -> None:
    expected = tmp_path / "donnees avec espaces et accents é"
    actual = preferred_user_data_root(
        {"GRAVITY_DATA_DIR": str(expected), "LOCALAPPDATA": "ignored"},
        platform_name="win32",
    )
    assert actual == expected


def test_windows_data_root_uses_local_app_data() -> None:
    actual = preferred_user_data_root(
        {"LOCALAPPDATA": r"C:\Users\Test\AppData\Local"},
        platform_name="win32",
    )
    assert actual == Path(r"C:\Users\Test\AppData\Local") / "Gravity"


def test_user_directories_are_created(tmp_path: Path) -> None:
    directories = ensure_user_directories(tmp_path / "Gravity")
    assert directories.root.is_dir()
    assert directories.logs.is_dir()
    assert directories.screenshots.is_dir()
    assert directories.cache.is_dir()
