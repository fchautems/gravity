"""Small native feedback surface available before the graphics stack starts."""

from __future__ import annotations

import ctypes
import sys

MESSAGE_BOX_OK = 0x00000000
MESSAGE_BOX_ICON_INFORMATION = 0x00000040
MESSAGE_BOX_ICON_ERROR = 0x00000010


def show_message(title: str, message: str, *, error: bool = False) -> None:
    """Show a Windows dialog, or print when running on another platform."""

    if sys.platform != "win32":
        stream = sys.stderr if error else sys.stdout
        print(f"{title}: {message}", file=stream)
        return

    style = MESSAGE_BOX_OK | (MESSAGE_BOX_ICON_ERROR if error else MESSAGE_BOX_ICON_INFORMATION)
    user32 = ctypes.windll.user32
    user32.MessageBoxW(None, message, title, style)
