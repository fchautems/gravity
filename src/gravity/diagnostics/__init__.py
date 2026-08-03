"""Logging, environment diagnostics, measurements, and timing summaries."""

from gravity.diagnostics.compatibility import CompatibilityReport, run_runtime_checks
from gravity.diagnostics.logging_setup import configure_logging

__all__ = ["CompatibilityReport", "configure_logging", "run_runtime_checks"]
