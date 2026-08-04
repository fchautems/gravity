# Gravity

Gravity is a modern, interactive 3D N-body gravity simulator being rebuilt from
a clean foundation.

The first release targets a visually polished, stable rotating galaxy with
10,000 particles on a consumer Windows PC. Python remains the application
language, while the expensive numerical loops and all particle rendering are
handled by compiled CPU code and the GPU.

## Status

**Step 7 complete: the 10,000 visible particles now evolve under the real
Barnes-Hut gravity engine through a non-blocking fixed-step worker.**

`LANCER_GRAVITY.bat` now opens a styled, resizable 3D window with a smooth orbit
camera, a French control panel, live frame and physics metrics, and 10,000
physical particles submitted in one GPU draw. The worker publishes only complete
immutable snapshots; rendering reuses the newest one and never waits for a
force calculation.

Barnes-Hut is the automatic and recommended backend. The exact `O(N²)` engine is
available only inside the collapsed advanced-physics section as an intentional
comparison mode. Activating it regenerates the scenario with a hard limit of
1,000 particles; returning to Barnes-Hut restores the 10,000-particle default.

The exact engine stores state in validated `float64` arrays, evaluates every
unordered pair once in compiled code, and advances it with kick-drift-kick
leapfrog. Its documented 100-orbit test is in the
[physics reference](docs/PHYSICS_REFERENCE.md).

The new [galaxy model](docs/GALAXY_MODEL.md) deterministically samples an
exponential disk and Hernquist bulge, computes a documented initial rotation
curve, keeps its Plummer halo separate from self-gravity, and removes global
position and velocity drift before the state reaches a solver.

The [Barnes-Hut engine](docs/BARNES_HUT.md) rebuilds a three-dimensional flat
octree for every force evaluation, traverses it in compiled parallel code, and
records tree and force timings separately. At the default theta, the seeded
10,000-particle benchmark reports 1.29% median acceleration error and 3.29% at
the 95th percentile, inside the 2% / 5% V1 limits.

## Windows quick start

1. Install 64-bit Python 3.12 from [python.org](https://www.python.org/downloads/).
2. Double-click `INSTALLER.bat` once.
3. Double-click `LANCER_GRAVITY.bat` to open the 3D application.
4. Double-click `TESTER_GRAVITY.bat` whenever you want the complete automated check.

No command needs to be typed. The environment lives in `.venv` beside the
project and logs live in `%LOCALAPPDATA%\Gravity\logs`. See the
[Windows installation guide](docs/INSTALLATION.md) for the exact first test and
troubleshooting path.

## Interactive test

- drag with the left mouse button to orbit;
- drag with the right or middle button to pan;
- use the wheel to zoom;
- use `Pause`, `Avancer d’un pas`, `Recommencer`, and `Recentrer la vue`;
- resize and maximize the window while watching the FPS overlay.
- optionally open `Physique avancée` to test the exact 1,000-particle reference,
  then return to Barnes-Hut.

The short [step-7 validation checklist](docs/STEP7_VALIDATION.md) records the
expected physical result and the useful information to report.

## V1 commitments

- 10,000 particles by default, with a supported range from 100 to 50,000.
- A deterministic rotating-galaxy scenario rather than a collapsing random cloud.
- A fixed-step leapfrog integrator and softened Newtonian gravity.
- An exact solver for small reference cases and Barnes-Hut for the interactive case.
- A single batched OpenGL draw for the particle field.
- A responsive French user interface with simple presets and advanced controls.
- Installation, launch, and tests by double-click on Windows.
- Numerical, integration, smoke, robustness, and performance tests from the start.
- Actionable error messages and local diagnostic logs; no telemetry.

The complete acceptance criteria are in the [V1 specification](docs/SPECIFICATION.md).

## Architecture

The planned stack is:

- Python 3.12 (64-bit)
- NumPy arrays for particle state
- Numba-compiled CPU kernels for intensive calculations
- ModernGL with an OpenGL 3.3 core context
- GLFW and Dear ImGui Bundle for the window, input, and controls
- Pytest, Ruff, and measured benchmarks for quality

Physics, rendering, scenarios, UI, and orchestration have strict boundaries so
that a future GPU, C++, or Rust physics backend can replace the CPU solver
without rewriting the application.

Read the [architecture](docs/ARCHITECTURE.md) and the recorded
[architecture decisions](docs/adr/README.md) for details.

## Roadmap

Development is split into small, runnable gates. Each visual or physical layer
is validated before the next one is added. See the [roadmap](docs/ROADMAP.md).

## Source layout

```text
src/gravity/
├── app/          # Lifecycle and orchestration
├── core/         # Stable data contracts and configuration
├── diagnostics/  # Logging, metrics, and timing
├── physics/      # Solvers and integrators
├── rendering/    # OpenGL renderer, shaders, and camera
├── scenarios/    # Reproducible initial conditions
└── ui/           # User controls and input mapping
```

The packages now include the startup boundary, local diagnostics, orbit camera,
input routing, dynamic ModernGL renderer, Dear ImGui shell, validated particle
state, exact force solver, leapfrog integrator, physical-invariant diagnostics,
analytic halo, reproducible physical galaxy generator, flat octree, parallel
Barnes-Hut solver, bounded snapshot exchange, command queue, and clean worker
lifecycle.

## Historical version

The original Python/Ursina implementation from 2020 is preserved in the
[`archive-gravity-2020`](https://github.com/fchautems/gravity/tree/archive-gravity-2020)
branch. It includes the first Barnes-Hut octree experiments and remains
available as a reference.
