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

At step 6 the ordinary suite also covers the strict particle-state boundary,
analytic softened two-body forces, pair-force antisymmetry, fixed-step leapfrog,
closed-form invariants, 100 complete binary orbits, deterministic galaxy
generation, flat-octree structure, coincident-particle termination, Barnes-Hut
accuracy, sequential/parallel equality, and solver/integrator composition.
Numba kernel bodies are excluded from Python line tracing because compiled
execution bypasses the tracer; their outputs and edge cases remain covered by
numerical tests. Graphics tests continue to cover camera, input capture, the
mocked single GPU draw, resource ownership, runtime imports, launchers, and
diagnostics. Real GLFW/OpenGL behaviour is checked with
`docs/GRAPHICS_VALIDATION.md`.
