"""Rotating local logs for startup and later application diagnostics."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from gravity.core.paths import ensure_user_directories

LOGGER_NAME = "gravity"
LOG_FILENAME = "gravity.log"
MAX_LOG_BYTES = 1_000_000
BACKUP_COUNT = 5


def configure_logging(data_root: Path | None = None) -> tuple[logging.Logger, Path]:
    """Configure one managed rotating file handler and return its path."""

    directories = ensure_user_directories(data_root)
    log_path = directories.logs / LOG_FILENAME
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in tuple(logger.handlers):
        if getattr(handler, "_gravity_managed", False):
            logger.removeHandler(handler)
            handler.close()

    handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler._gravity_managed = True  # type: ignore[attr-defined]
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger, log_path
