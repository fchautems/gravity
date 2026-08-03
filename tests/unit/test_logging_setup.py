from __future__ import annotations

import logging
from pathlib import Path

from gravity.diagnostics.logging_setup import configure_logging


def test_configure_logging_writes_to_selected_root(tmp_path: Path) -> None:
    logger, log_path = configure_logging(tmp_path / "user data")
    logger.info("diagnostic test")
    for handler in logger.handlers:
        handler.flush()

    assert log_path == tmp_path / "user data" / "logs" / "gravity.log"
    assert "diagnostic test" in log_path.read_text(encoding="utf-8")


def test_reconfiguration_keeps_only_one_managed_handler(tmp_path: Path) -> None:
    logger, _ = configure_logging(tmp_path / "first")
    logger, _ = configure_logging(tmp_path / "second")
    managed = [
        handler for handler in logger.handlers if getattr(handler, "_gravity_managed", False)
    ]
    assert len(managed) == 1
    assert isinstance(managed[0], logging.Handler)
