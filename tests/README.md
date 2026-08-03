# Tests

Tests are added with the implementation they verify; this directory does not
contain passing placeholders.

The planned suites are:

- `unit/`: validation, array contracts, math, and camera behaviour;
- `physics/`: analytic systems, conservation, octree structure, and solver error;
- `integration/`: commands, lifecycle, snapshots, settings, reset, and shutdown;
- `smoke/`: application startup and real-OpenGL checks.

Deterministic correctness tests run in the ordinary test command. Hardware and
long-running tests use explicit markers. See `docs/SPECIFICATION.md` and
`docs/ARCHITECTURE.md` for thresholds and release policy.

