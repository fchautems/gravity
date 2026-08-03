"""User-data locations shared by diagnostics and the application."""

from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

APP_DIRECTORY_NAME = "Gravity"
DATA_DIR_ENVIRONMENT_VARIABLE = "GRAVITY_DATA_DIR"


@dataclass(frozen=True, slots=True)
class UserDirectories:
    """Writable locations owned by Gravity for one user."""

    root: Path
    logs: Path
    screenshots: Path
    cache: Path


def preferred_user_data_root(
    environment: Mapping[str, str] | None = None,
    platform_name: str | None = None,
) -> Path:
    """Return the preferred data root without creating it."""

    values = os.environ if environment is None else environment
    explicit = values.get(DATA_DIR_ENVIRONMENT_VARIABLE)
    if explicit:
        return Path(explicit).expanduser()

    selected_platform = sys.platform if platform_name is None else platform_name
    if selected_platform == "win32":
        local_app_data = values.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_DIRECTORY_NAME

    if selected_platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIRECTORY_NAME

    xdg_data_home = values.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / APP_DIRECTORY_NAME
    return Path.home() / ".local" / "share" / APP_DIRECTORY_NAME


def ensure_user_directories(root: Path | None = None) -> UserDirectories:
    """Create Gravity's writable directories, with a temporary fallback."""

    preferred = preferred_user_data_root() if root is None else root
    fallback = Path(tempfile.gettempdir()) / APP_DIRECTORY_NAME
    candidates = (preferred,) if preferred == fallback else (preferred, fallback)

    last_error: OSError | None = None
    for candidate in candidates:
        directories = UserDirectories(
            root=candidate,
            logs=candidate / "logs",
            screenshots=candidate / "screenshots",
            cache=candidate / "cache",
        )
        try:
            for directory in (
                directories.root,
                directories.logs,
                directories.screenshots,
                directories.cache,
            ):
                directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            last_error = error
            continue
        return directories

    message = "Impossible de creer le dossier de donnees de Gravity."
    raise RuntimeError(message) from last_error
