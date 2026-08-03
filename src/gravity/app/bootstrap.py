"""Top-level application boundary used by the Windows launcher."""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from collections.abc import Sequence

from gravity import __version__
from gravity.app.user_feedback import show_message
from gravity.core.errors import ApplicationStartupError
from gravity.diagnostics import configure_logging, run_runtime_checks

EXIT_SUCCESS = 0
EXIT_UNEXPECTED_ERROR = 1
EXIT_INCOMPATIBLE_RUNTIME = 2
EXIT_APPLICATION_ERROR = 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gravity startup and diagnostics")
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="run the non-graphical compatibility checks and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit diagnostic output as JSON (requires --diagnostic)",
    )
    parser.add_argument(
        "--skip-jit",
        action="store_true",
        help="skip the compiled Numba smoke calculation",
    )
    parser.add_argument(
        "--no-dialog",
        action="store_true",
        help="do not display a native status dialog",
    )
    return parser


def _log_report(logger: logging.Logger, report_lines: Sequence[str]) -> None:
    for line in report_lines:
        logger.info("Runtime check: %s", line)


def _run_application(logger: logging.Logger) -> None:
    """Import graphics only after the non-graphical startup checks have passed."""

    from gravity.app.graphics_app import run_graphics_app

    run_graphics_app(logger)


def main(arguments: Sequence[str] | None = None) -> int:
    """Validate startup, then hand over to the current application milestone."""

    options = _parser().parse_args(arguments)
    logger, log_path = configure_logging()
    logger.info("Gravity %s startup", __version__)

    try:
        report = run_runtime_checks(run_jit=not options.skip_jit)
        _log_report(logger, report.to_lines())

        if options.diagnostic:
            output = report.to_json() if options.json else "\n".join(report.to_lines())
            print(output)

        if not report.ok:
            message = (
                "L'environnement de Gravity n'est pas compatible.\n\n"
                f"Consultez le diagnostic dans :\n{log_path}\n\n"
                "Relancez INSTALLER.bat pour reparer l'installation."
            )
            if not options.no_dialog and not options.diagnostic:
                show_message("Gravity - erreur", message, error=True)
            return EXIT_INCOMPATIBLE_RUNTIME

        if options.diagnostic:
            return EXIT_SUCCESS

        _run_application(logger)
        return EXIT_SUCCESS
    except ApplicationStartupError as error:
        logger.exception("Application startup failure")
        message = (
            "Gravity ne peut pas ouvrir la fenetre 3D.\n\n"
            f"{error}\n\n"
            f"Le diagnostic a ete enregistre dans :\n{log_path}"
        )
        if not options.no_dialog:
            show_message("Gravity - erreur graphique", message, error=True)
        else:
            print(message, file=sys.stderr)
        return EXIT_APPLICATION_ERROR
    except Exception:  # noqa: BLE001 - final application exception boundary
        logger.exception("Unexpected startup failure")
        message = (
            "Gravity a rencontre une erreur inattendue.\n\n"
            f"Le diagnostic a ete enregistre dans :\n{log_path}"
        )
        if not options.no_dialog:
            show_message("Gravity - erreur", message, error=True)
        else:
            print(message, file=sys.stderr)
            traceback.print_exc()
        return EXIT_UNEXPECTED_ERROR
