"""Dependency-free installer and quality runner used by the Windows batch files."""

from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys
import tempfile
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TextIO

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VIRTUAL_ENVIRONMENT = PROJECT_ROOT / ".venv"
LOCK_FILE = PROJECT_ROOT / "requirements" / "step2.lock"
SUPPORTED_PYTHON = (3, 12)
PIP_VERSION = "26.2"
SETUPTOOLS_VERSION = "83.0.0"


class BootstrapError(RuntimeError):
    """Expected setup failure with a message suitable for the user."""


@dataclass(frozen=True, slots=True)
class InterpreterInfo:
    """Small, stable description of a Python executable."""

    implementation: str
    major: int
    minor: int
    bits: int


def _data_root(environment: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environment is None else environment
    explicit = values.get("GRAVITY_DATA_DIR")
    if explicit:
        return Path(explicit).expanduser()
    local_app_data = values.get("LOCALAPPDATA")
    if sys.platform == "win32" and local_app_data:
        return Path(local_app_data) / "Gravity"
    return Path(tempfile.gettempdir()) / "Gravity"


def _new_log_path(action: str) -> Path:
    preferred = _data_root() / "logs"
    fallback = Path(tempfile.gettempdir()) / "Gravity" / "logs"
    for directory in (preferred, fallback):
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        return directory / f"{action}-{timestamp}.log"
    raise BootstrapError("Impossible de creer un journal d'installation.")


def _emit(message: str, log_file: TextIO) -> None:
    print(message, flush=True)
    log_file.write(f"{message}\n")
    log_file.flush()


def _run_command(
    command: Sequence[str],
    log_file: TextIO,
    *,
    environment: Mapping[str, str] | None = None,
) -> None:
    rendered = " ".join(command)
    _emit(f"> {rendered}", log_file)
    encoding = "utf-8"
    process = subprocess.Popen(
        list(command),
        cwd=PROJECT_ROOT,
        env=None if environment is None else dict(environment),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding=encoding,
        errors="replace",
    )
    if process.stdout is None:
        raise BootstrapError("Impossible de lire la sortie du programme lance.")
    for line in process.stdout:
        clean_line = line.rstrip("\r\n")
        _emit(clean_line, log_file)
    return_code = process.wait()
    if return_code != 0:
        raise BootstrapError(f"La commande a echoue avec le code {return_code}: {rendered}")


def _venv_python(
    virtual_environment: Path = VIRTUAL_ENVIRONMENT,
    *,
    platform_name: str | None = None,
) -> Path:
    selected_platform = sys.platform if platform_name is None else platform_name
    if selected_platform == "win32":
        return virtual_environment / "Scripts" / "python.exe"
    return virtual_environment / "bin" / "python"


def _inspect_interpreter(executable: Path) -> InterpreterInfo | None:
    probe = (
        "import json, platform, struct, sys; "
        "print(json.dumps({'implementation': platform.python_implementation(), "
        "'major': sys.version_info.major, 'minor': sys.version_info.minor, "
        "'bits': struct.calcsize('P') * 8}))"
    )
    try:
        completed = subprocess.run(
            [str(executable), "-c", probe],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        values = json.loads(completed.stdout)
        return InterpreterInfo(
            implementation=str(values["implementation"]),
            major=int(values["major"]),
            minor=int(values["minor"]),
            bits=int(values["bits"]),
        )
    except (
        OSError,
        subprocess.SubprocessError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None


def _current_interpreter() -> InterpreterInfo:
    return InterpreterInfo(
        implementation=sys.implementation.name,
        major=sys.version_info.major,
        minor=sys.version_info.minor,
        bits=struct.calcsize("P") * 8,
    )


def _is_supported(info: InterpreterInfo) -> bool:
    return (
        info.implementation.lower() == "cpython"
        and (info.major, info.minor) == SUPPORTED_PYTHON
        and info.bits == 64
    )


def _next_backup_path(
    virtual_environment: Path = VIRTUAL_ENVIRONMENT,
    *,
    timestamp: str | None = None,
) -> Path:
    suffix = datetime.now().strftime("%Y%m%d-%H%M%S") if timestamp is None else timestamp
    candidate = virtual_environment.with_name(f"{virtual_environment.name}-incompatible-{suffix}")
    counter = 2
    while candidate.exists():
        candidate = virtual_environment.with_name(
            f"{virtual_environment.name}-incompatible-{suffix}-{counter}"
        )
        counter += 1
    return candidate


def _child_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.setdefault("PYTHONUTF8", "1")
    cache = _data_root(environment) / "cache" / "numba"
    cache.mkdir(parents=True, exist_ok=True)
    environment.setdefault("NUMBA_CACHE_DIR", str(cache))
    return environment


def _ensure_virtual_environment(log_file: TextIO) -> Path:
    python_path = _venv_python()
    if VIRTUAL_ENVIRONMENT.exists():
        existing = _inspect_interpreter(python_path)
        if existing is not None and _is_supported(existing):
            _emit("Environnement Python 3.12 64 bits existant reutilise.", log_file)
            return python_path

        backup = _next_backup_path()
        _emit(f"Ancien environnement incompatible conserve dans: {backup.name}", log_file)
        try:
            VIRTUAL_ENVIRONMENT.rename(backup)
        except OSError as error:
            raise BootstrapError(
                "Impossible de deplacer l'ancien dossier .venv. Fermez les programmes qui l'utilisent."
            ) from error

    _emit("Creation de l'environnement Python local .venv...", log_file)
    _run_command([sys.executable, "-m", "venv", str(VIRTUAL_ENVIRONMENT)], log_file)
    created = _inspect_interpreter(python_path)
    if created is None or not _is_supported(created):
        raise BootstrapError("L'environnement cree n'utilise pas CPython 3.12 en 64 bits.")
    return python_path


def install(log_file: TextIO) -> None:
    """Create the local environment, install the lock, and run a compiled smoke test."""

    current = _current_interpreter()
    if not _is_supported(current):
        raise BootstrapError(
            "INSTALLER.bat doit utiliser CPython 3.12 en 64 bits. "
            "Installez Python 3.12 depuis python.org puis relancez-le."
        )
    if not LOCK_FILE.is_file():
        raise BootstrapError(f"Fichier de dependances introuvable: {LOCK_FILE}")

    environment = _child_environment()
    python_path = _ensure_virtual_environment(log_file)
    _emit("Mise a niveau des outils d'installation...", log_file)
    _run_command(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--quiet",
            f"pip=={PIP_VERSION}",
            f"setuptools=={SETUPTOOLS_VERSION}",
        ],
        log_file,
        environment=environment,
    )
    _emit("Installation de l'environnement Gravity verrouille...", log_file)
    _run_command(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--only-binary=:all:",
            "--requirement",
            str(LOCK_FILE),
        ],
        log_file,
        environment=environment,
    )
    _run_command(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            "--no-build-isolation",
            "--editable",
            str(PROJECT_ROOT),
        ],
        log_file,
        environment=environment,
    )
    _emit("Verification des dependances et compilation Numba...", log_file)
    _run_command([str(python_path), "-m", "pip", "check"], log_file, environment=environment)
    _run_command(
        [str(python_path), "-m", "gravity", "--diagnostic", "--json"],
        log_file,
        environment=environment,
    )
    _emit("Installation terminee avec succes.", log_file)


def run_quality_checks(log_file: TextIO) -> None:
    """Run the complete non-graphical step-2 verification suite."""

    python_path = _venv_python()
    info = _inspect_interpreter(python_path)
    if info is None or not _is_supported(info):
        raise BootstrapError("Installation absente ou invalide. Lancez d'abord INSTALLER.bat.")

    environment = _child_environment()
    commands = (
        [str(python_path), "-m", "compileall", "-q", "src", "tools", "tests"],
        [str(python_path), "-m", "ruff", "check", "."],
        [str(python_path), "-m", "ruff", "format", "--check", "."],
        [str(python_path), "-m", "mypy"],
        [
            str(python_path),
            "-m",
            "pytest",
            "-q",
            "--cov=gravity",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
        ],
        [str(python_path), "-m", "pip", "check"],
    )
    for command in commands:
        _run_command(command, log_file, environment=environment)
    _emit("Tous les controles de l'etape 2 ont reussi.", log_file)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gravity setup helper")
    parser.add_argument("action", choices=("install", "test"))
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    options = _parser().parse_args(arguments)
    log_path = _new_log_path(options.action)
    try:
        with log_path.open("w", encoding="utf-8", newline="\n") as log_file:
            _emit(f"Gravity - action: {options.action}", log_file)
            _emit(f"Dossier du projet: {PROJECT_ROOT}", log_file)
            if options.action == "install":
                install(log_file)
            else:
                run_quality_checks(log_file)
            _emit(f"Journal: {log_path}", log_file)
        return 0
    except (BootstrapError, OSError) as error:
        message = f"ECHEC: {error}"
        print(message, file=sys.stderr)
        try:
            with log_path.open("a", encoding="utf-8", newline="\n") as log_file:
                log_file.write(f"{message}\n")
                log_file.write(traceback.format_exc())
        except OSError:
            pass
        print(f"Journal: {log_path}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
