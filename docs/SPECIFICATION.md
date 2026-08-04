# Gravity V1 specification

Status: approved baseline for implementation  
Last updated: 2026-08-04

## 1. Product promise

Gravity V1 is a Windows desktop application that lets a non-specialist launch
and explore a convincing rotating 3D galaxy without opening a terminal or
editing configuration files.

It is both a visual simulator and a trustworthy numerical foundation. A pretty
result is not accepted if the motion is numerically broken; a correct solver is
not accepted if the application is awkward to install or use.

## 2. Primary target

The reference machine is the project's owner's current PC:

- Windows 10 or Windows 11, 64-bit;
- NVIDIA GTX 1070-class GPU or better, with a current vendor driver;
- 16 GB RAM;
- Python installed from python.org;
- a conventional 1920 x 1080 desktop, including Windows display scaling.

The V1 is Windows-first. Keeping the code portable is required, but Linux and
macOS packaging are not release gates.

## 3. First-use journey

1. The user double-clicks `INSTALLER.bat` once.
2. The installer creates an isolated local environment, installs pinned
   dependencies, runs a compatibility check, and reports success or a useful
   error in French.
3. The user double-clicks `LANCER_GRAVITY.bat`.
4. Gravity opens on the `Galaxie spirale` preset with 10,000 particles.
5. The camera can immediately orbit, pan, and zoom with the mouse.
6. The user can pause, resume, advance one physics step, reset the current
   state, or regenerate it from a chosen seed.
7. Simple presets are visible first; technical parameters live in a collapsed
   advanced section.
8. Closing and reopening Gravity restores safe visual preferences and the last
   selected preset. It never silently resumes an unfinished simulation.

## 4. Functional requirements

| ID | Requirement | V1 acceptance |
|---|---|---|
| F-01 | One-click setup | Installation needs no typed command and works from a path containing spaces and accents. |
| F-02 | One-click launch | Normal launch leaves no console window open and either opens the application or a useful error dialog. |
| F-03 | Default scenario | `Galaxie spirale` creates 10,000 finite particles and starts with stable, coherent rotation. |
| F-04 | Camera | Orbit, pan, zoom, reset view, and fullscreen are smooth and do not alter simulation state. |
| F-05 | Time controls | Pause, resume, single-step, reset, and time-scale controls behave deterministically. |
| F-06 | Regeneration | Particle count, seed, galaxy size, mass model, and structure parameters clearly require regeneration. |
| F-07 | Live controls | Camera, particle size, exposure, colour mode, trails/glow, and time scale can change without regeneration. |
| F-08 | Presets | `Qualité`, `Équilibré`, and `Performance` choose coherent visual and numerical settings. |
| F-09 | Observability | The UI exposes FPS, physics steps/s, particle count, simulation time, solver, and tree-build/force timing. |
| F-10 | Reproducibility | A seed plus a complete scenario configuration reproduces the same initial state on the same numeric backend. |
| F-11 | Screenshot | A shortcut and button save a timestamped PNG and report its location. |
| F-12 | Persistence | Safe preferences are stored outside the repository and invalid settings fall back to defaults. |
| F-13 | Diagnostics | Failures create a rotating local log and show the log path without exposing private machine data unnecessarily. |
| F-14 | Clean shutdown | Closing during active simulation stops workers and releases graphics resources without hanging. |

## 5. Physics requirements

| ID | Requirement |
|---|---|
| P-01 | Use softened Newtonian gravity in three spatial dimensions. |
| P-02 | Store and integrate physics state in `float64`; rendering may consume a `float32` snapshot. |
| P-03 | Use a fixed simulation time step and kick-drift-kick leapfrog integration. |
| P-04 | Provide an exact symmetric direct solver as the reference for small systems. |
| P-05 | Provide a three-dimensional Barnes-Hut octree for interactive particle counts. |
| P-06 | Rebuild the tree from current positions for every Barnes-Hut force evaluation. |
| P-07 | Keep self-gravity separate from optional analytic galaxy potentials. |
| P-08 | Use dimensionless internal units with `G = 1`; presentation units are a separate concern. |
| P-09 | Reject NaN, infinity, negative mass, non-positive time step, and invalid solver parameters at boundaries. |
| P-10 | Do not delete particles merely because they move outside their initial galaxy radius. |

Collisions, mergers, gas, relativistic effects, and stellar evolution are not
part of V1 physics.

## 6. User-interface requirements

- The V1 interface language is French; code, identifiers, and developer
  documentation remain English.
- The default appearance is a restrained dark space theme with high-contrast
  controls and no decorative clutter.
- The 3D viewport is the dominant surface. A docked control panel may be hidden.
- Basic controls must be understandable without knowing what an octree,
  softening length, or theta means.
- Barnes-Hut is the automatic interactive default. The exact solver is exposed
  only as an advanced comparison mode and must enforce a safe particle ceiling.
- Every advanced numeric control has a safe range, a default, a short tooltip,
  and either immediate or `Régénérer` semantics.
- UI input takes priority over camera input while the pointer is over a widget.
- Layout and font sizes must remain usable from 100% to 200% Windows scaling.
- During first JIT compilation the app displays progress instead of appearing
  frozen.
- No ordinary user action should require editing JSON, Python, or shader files.

## 7. Visual direction

The galaxy should read clearly at a glance:

- a warm, dense core;
- cooler outer arms with subtle colour variation;
- depth conveyed by brightness, size, and camera motion;
- smooth circular point sprites rather than square pixels;
- optional additive glow and short trails, both independently disableable;
- no heavy sky texture that competes with the simulated particles.

Visual effects must never modify physics data. Performance measurements can
disable each effect separately.

## 8. Measurable quality targets

Targets are measured in release mode after JIT warm-up on the reference PC.
They are budgets, not claims made before implementation.

### Rendering and responsiveness

| Measure | V1 target |
|---|---:|
| Static/paused 10,000-particle viewport at 1920 x 1080 | median >= 60 FPS |
| Active default simulation | UI median >= 30 FPS |
| Normal control response | < 100 ms |
| Position upload and base particle draw | < 4 ms median |
| Working set for default scenario, excluding display-driver allocation | < 500 MB |
| Unattended default run | 30 minutes without crash, hang, NaN, or unbounded log growth |

The step-6 solver-only gate requires Barnes-Hut to be at least 10x faster than
the exact solver at 10,000 particles on the same warmed host; the measured
baseline is 26.92x. Absolute physics steps per second are recorded on the
reference Windows PC during step 7, when the worker competes with the real UI
and renderer. Responsiveness remains a hard gate even if the simulation clock
advances more slowly than real time.

### Numerical reference tests

| Measure | V1 target |
|---|---:|
| Two-body circular-orbit relative energy drift after 100 orbits | < 0.1% with the documented test step |
| Isolated direct-solver centre-of-mass drift | <= 1e-9 in normalized test units |
| Direct pair-force antisymmetry | within `float64` test tolerance |
| Barnes-Hut acceleration error, default theta, seeded validation sets | median <= 2%; 95th percentile <= 5% |
| Barnes-Hut speedup over exact solver, warmed 10,000-particle same-host case | >= 10x |
| Scenario reproducibility | exact initial arrays for a fixed seed and environment |

Barnes-Hut relative errors exclude reference accelerations below a documented
near-zero floor; absolute error is reported for those samples.

## 9. Supported operating range

| Setting | V1 range | Default |
|---|---:|---:|
| Visible particles | 100 to 50,000 | 10,000 |
| Barnes-Hut theta | 0.3 to 1.2 | 0.7, validated at step 6 |
| Time scale | paused to 20x visual speed | 1x |
| Seed | unsigned 32-bit integer | fixed documented seed |
| Galaxy softening | 0.02 to 0.25 | 0.08 |
| Fixed galaxy time step | 0.0025 to 0.08 | 0.02 |
| Disk outer radius | 6.0 to 24.0 | 10.8 |

These are dimensionless internal values. Step 5 validates the physical scenario
ranges; step 8 will decide how much of each safe range is exposed in the basic
and advanced interface. Component-mass editing remains advanced and must
preserve strictly positive live-particle masses.

## 10. Test and release policy

Every implementation step must leave a runnable or objectively verifiable
state. A step is complete only when its own tests pass.

Required layers are:

- unit tests for validation, state, math, and camera behaviour;
- deterministic numerical tests against analytic or exact reference cases;
- Barnes-Hut structure and error-comparison tests;
- integration tests for commands, reset, and snapshot exchange;
- graphics smoke tests on a machine with a real OpenGL context;
- installer/launcher smoke tests on Windows;
- manual visual checks for camera feel, DPI scaling, and appearance;
- benchmarks kept separate from ordinary pass/fail unit tests;
- a 30-minute release soak test.

No performance claim is accepted without recording machine, particle count,
configuration, warm-up state, and measurement distribution.

## 11. Explicitly outside V1

- particle collision or merger logic;
- two-galaxy collisions;
- gas or hydrodynamics;
- relativistic gravity or black-hole accretion;
- compute-shader, CUDA, or distributed physics;
- hundreds of thousands or millions of live particles;
- a complete scenario editor;
- save/resume of arbitrary simulation state;
- an online service, accounts, telemetry, or network dependency at runtime;
- a standalone `.exe` installer (evaluated after the source V1 is stable);
- scientific claims about real galaxy formation.

## 12. V1 release gate

V1 is ready only when all of the following are true:

- the first-use journey succeeds on a clean Windows user account;
- all automated non-performance tests pass;
- exact and Barnes-Hut validation reports meet their thresholds;
- the default scenario meets responsiveness and stability budgets;
- every UI value is validated and reset/restart paths are reliable;
- screenshots, settings, and logs use documented user-data locations;
- the reference user completes the basic workflow without source code or a
  terminal;
- README and troubleshooting instructions match the delivered program.
