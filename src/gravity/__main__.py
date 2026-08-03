"""Allow ``python -m gravity`` to use the stable application entrypoint."""

from __future__ import annotations

from gravity.app.bootstrap import main

if __name__ == "__main__":
    raise SystemExit(main())
