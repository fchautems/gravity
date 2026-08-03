# Gravity

Gravity is a modern, interactive 3D N-body gravity simulator being rebuilt from
a clean foundation.

The first release targets a visually polished, stable rotating galaxy with
10,000 particles on a consumer Windows PC. Python remains the application
language, while the expensive numerical loops and all particle rendering are
handled by compiled CPU code and the GPU.

## Status

**Step 2 complete: the Windows setup, launch, and test paths are reproducible.**

The numerical and graphics engines are not implemented yet. The current
launcher verifies the pinned Python/Numba foundation and displays a native
status message. Step 3 replaces that milestone message with the first 3D window,
camera, controls, and batched particle renderer.

## Windows quick start

1. Install 64-bit Python 3.12 from [python.org](https://www.python.org/downloads/).
2. Double-click `INSTALLER.bat` once.
3. Double-click `LANCER_GRAVITY.bat` to validate the installed application entrypoint.
4. Double-click `TESTER_GRAVITY.bat` whenever you want the complete automated check.

No command needs to be typed. The environment lives in `.venv` beside the
project and logs live in `%LOCALAPPDATA%\Gravity\logs`. See the
[Windows installation guide](docs/INSTALLATION.md) for the exact first test and
troubleshooting path.

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

The packages now include the startup boundary, local diagnostics, and the
compiled Numba compatibility smoke test. Simulation implementations arrive in
the roadmap step where they can be tested meaningfully.

## Historical version

The original Python/Ursina implementation from 2020 is preserved in the
[`archive-gravity-2020`](https://github.com/fchautems/gravity/tree/archive-gravity-2020)
branch. It includes the first Barnes-Hut octree experiments and remains
available as a reference.
