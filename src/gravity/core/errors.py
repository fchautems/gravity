"""Expected application failures that can be explained directly to the user."""


class ApplicationStartupError(RuntimeError):
    """A startup failure with a safe, actionable user-facing message."""
