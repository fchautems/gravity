"""Logging, environment diagnostics, accuracy reports, and timing summaries."""

from gravity.diagnostics.compatibility import CompatibilityReport, run_runtime_checks
from gravity.diagnostics.logging_setup import configure_logging
from gravity.diagnostics.solver_accuracy import (
    AccelerationErrorReport,
    compare_accelerations,
)

__all__ = [
    "AccelerationErrorReport",
    "CompatibilityReport",
    "compare_accelerations",
    "configure_logging",
    "run_runtime_checks",
]
