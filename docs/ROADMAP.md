# Gravity implementation roadmap

This roadmap turns the V1 specification into independently verifiable gates.
Only one gate is implemented at a time. A later gate may not hide a failure in an
earlier one.

## Progress

| Step | Deliverable | Exit criterion | Status |
|---:|---|---|---|
| 1 | V1 specification and architecture | Scope, budgets, module boundaries, numerical model, and test strategy are recorded; source package skeleton exists. | **Complete** |
| 2 | Reproducible setup and double-click launchers | Clean Windows setup, launch, and test smoke path work without a typed command; failures produce useful output. | **Complete** |
| 3 | Graphics shell | Styled window, UI panel, camera, and a single GPU draw render 10,000 synthetic points smoothly. | **Complete — Windows validation passed** |
| 4 | Exact physics reference | Direct solver and leapfrog pass two-body, conservation, symmetry, and long-run tests. | **Complete** |
| 5 | Galaxy generator | A seeded disk/bulge/halo configuration rotates coherently and passes distribution tests. | **Complete** |
| 6 | Barnes-Hut | Flat octree passes structure tests, meets error budgets against exact forces, and demonstrates measured speedup. | **Complete** |
| 7 | Physics/render coupling | Fixed-step worker, command queue, snapshots, pause/step/reset, and clean shutdown are reliable. | **Complete** |
| 8 | Initial-condition laboratory | Particle count, eight seeded scenarios, repeat/reroll controls, workload guidance, and exact-mode safeguards are usable. | **Complete** |
| 9 | Observe the physics | Colour modes, ejection state, statistics, centre of mass, and canonical views make the evolution understandable. | **Complete** |
| 10 | Record and replay | Bounded history, timeline, seeking, frame stepping, and accelerated playback coexist with live simulation. | Planned |
| 11 | Follow individual particles | Picking, highlight, recent trajectory, trails, and a follow camera remain usable at interactive counts. | Planned |
| 12 | Optional particle mergers | Spatially accelerated finite-radius detection and momentum-conserving fusion are physically explicit and disableable. | Planned |
| 13 | Finish and publish | Presets, capture/export, hidden UI, persistence, robustness, benchmarks, documentation, and release workflow are polished. | Planned |

## Step 1 output

Step 1 creates no simulation placeholder. Its durable output is:

- `docs/SPECIFICATION.md`: what V1 must do and how success is measured;
- `docs/ARCHITECTURE.md`: how the system is separated and how data moves;
- `docs/adr/`: decisions that should not drift silently;
- `src/gravity/`: package boundaries with no fake implementation;
- `tests/README.md` and `benchmarks/README.md`: verification rules.

## Step 2 output

Step 2 establishes the first executable and testable project boundary:

- `INSTALLER.bat`: locates 64-bit CPython 3.12 and creates a repository-local
  `.venv` from the complete step-2 lock;
- `LANCER_GRAVITY.bat`: starts `pythonw` from the isolated environment without a
  persistent console;
- `TESTER_GRAVITY.bat`: runs syntax, lint, typing, tests, coverage, and package
  consistency checks;
- `tools/bootstrap.py`: preserves an incompatible old environment, streams
  useful progress, and records install/test logs;
- `gravity.diagnostics`: validates exact package versions and executes a real,
  cached Numba compilation;
- `gravity.app.bootstrap`: provides the top-level exception boundary and native
  status/error feedback used before graphics initialization.

The graphics packages remain outside the step-2 lock on purpose. They are
pinned only after the integrated GLFW / ModernGL / Dear ImGui Bundle smoke gate
at the beginning of step 3.

## Step 3 output

Step 3 replaces the milestone dialog with the first real application window:

- GLFW creates a resizable OpenGL 3.3 core window with DPI-aware sizing;
- ModernGL renders one interleaved NumPy buffer containing 10,000 synthetic
  particles in exactly one base draw call;
- the shaders animate a clearly labelled visual-only galaxy cloud and render
  soft circular point sprites;
- a tested orbit camera supports left-drag orbit, right/middle-drag pan, wheel
  zoom, and reset;
- Dear ImGui provides a restrained French panel, pause/restart controls, live
  sizing, GPU information, FPS, and render-time medians;
- camera input is latched outside UI widgets so sliders never move the view;
- shutdown releases particle, UI, context, and GLFW resources in ownership
  order.

The complete non-hardware suite contains 54 tests at this gate. Shader and
window creation still require the short native Windows check in
`GRAPHICS_VALIDATION.md`; a headless container cannot prove the target driver's
OpenGL context or DPI behaviour.

The graphics gate was subsequently validated on a Windows work PC with Intel
UHD integrated graphics: 10,000 particles rendered at the display-limited 60
FPS, with orbit, pan, zoom, controls, and resize behaving correctly. A later
reference-PC run remains useful but does not block the independent physics
steps.

## Step 4 output

Step 4 adds the independent numerical reference required before Barnes-Hut:

- `ParticleState` enforces finite, C-contiguous `float64` state arrays, positive
  masses, and unique `uint64` IDs;
- `ExactGravitySolver` evaluates each pair once and writes equal/opposite pair
  forces through a cached, non-fast-math Numba kernel;
- `LeapfrogIntegrator` implements fixed-step kick-drift-kick and reuses the
  final acceleration safely between consecutive advances;
- invariant helpers measure centre of mass, momentum, angular momentum, and
  softened total energy;
- analytic, invalid-boundary, compiled-vs-Python, and 100-orbit tests establish
  the exact solver as the future Barnes-Hut oracle.

At this gate the complete automated suite contains 98 tests with 87.39% branch
coverage. The documented circular binary has relative energy drift `2.67e-9`
after 100 orbits and centre-of-mass drift `3.76e-13`, both well inside the V1
budgets. See `docs/PHYSICS_REFERENCE.md` for the model and reproducible test
parameters.

## Step 5 output

Step 5 adds deterministic, physically motivated galactic initial conditions:

- `GalaxyConfig` validates the complete seed, structure, mass, dispersion,
  softening, and fixed-step configuration;
- the generator samples a truncated exponential disk, truncated spherical
  Hernquist bulge, and optional live central mass into strict `float64` arrays;
- `GalaxyMassModel` derives initial tangential speeds from a documented smooth
  enclosed-mass curve and applies small seeded dispersions;
- `PlummerPotential` models the non-particle halo as a separate compiled
  analytic field, while `CompositeGravitySolver` composes it explicitly with
  exact or future Barnes-Hut self-gravity;
- mass-weighted position and bulk velocity are corrected before deterministic
  shuffling, producing effectively zero centre-of-mass drift and momentum;
- distribution, determinism, analytic-potential, rotation-coherence, and
  240-particle exact dynamic tests validate the gate without graphics.

At this gate the complete automated suite contains 147 tests with 88.84% branch
coverage. In the short dynamic gate, the median disk radius remains at `0.996`
of its initial value after 200 steps while its median angular travel reaches
`0.513` radians. See `docs/GALAXY_MODEL.md` for formulas, defaults, caveats, and
the complete measured evidence.

## Step 6 output

Step 6 adds the measured approximation used by the interactive worker from
step 7 onward:

- `FlatOctree` stores cubic bounds, child indices, nested particle ranges,
  depths, masses, and centres of mass in immutable contiguous arrays;
- the deterministic compiled builder partitions only occupied octants, grows
  storage safely for adversarial distributions, and stops coincident particles
  at a validated depth limit;
- `BarnesHutSolver` always opens nodes containing the target particle, evaluates
  leaf neighbours directly, and accepts distant monopoles with configurable
  theta;
- sequential traversal avoids overhead for small systems, while parallel Numba
  traversal handles the interactive range with bitwise-identical results;
- `BarnesHutStats` separates tree-build and force time and records structural
  and interaction counts;
- exact-versus-approximate reports isolate near-zero reference accelerations and
  enforce the 2% median / 5% 95th-percentile gate.

At this gate the complete automated suite contains 188 tests with 88.90% branch
coverage. The 512-particle galaxy validation measures 1.142% median and 3.125%
95th-percentile error. In the committed nine-thread benchmark, the default
10,000-particle case takes 11.509 ms versus 309.888 ms for the exact solver, a
26.92x speedup, with 1.291% / 3.294% error. See `docs/BARNES_HUT.md` and the
machine-readable benchmark baseline for the complete method and caveats.

## Step 7 output

Step 7 replaces the visual-only shader animation with the complete physical
pipeline:

- `PhysicsWorker` is the only owner of mutable `float64` physics state and runs
  fixed leapfrog steps outside the OpenGL/UI thread;
- a typed command queue handles pause, resume, single step, deterministic reset,
  time scale, solver switch, and shutdown at safe points;
- a queue of capacity one publishes complete, read-only `float32` position
  snapshots, dropping superseded presentation copies but never physics state;
- the renderer uploads only a newly available snapshot, retains one interleaved
  GPU buffer, and issues one particle draw without any shader-side rotation;
- Barnes-Hut is always the startup backend with 10,000 particles;
- the exact solver is deliberately hidden in the collapsed advanced section,
  explicitly labelled as a comparison tool, and hard-limited to 1,000 particles;
- reset and backend changes regenerate the same seeded scenario, while switching
  back to Barnes-Hut restores the 10,000-particle default;
- worker failures are relayed to the main application boundary and shutdown has
  a bounded join instead of leaving an invisible background thread.

The complete automated suite contains 198 tests with branch coverage above the
80% delivery gate. A real warmed coupling smoke in the validation container
started Barnes-Hut with 10,000 particles, advanced four finite steps, and
reported 13.35 ms for the last force/integration step. The exact comparison mode
switched to 1,000 particles, advanced one step in 8.81 ms, and restored the
paused 10,000-particle Barnes-Hut state. A second short soak reached 100 steps
with finite positions and stopped the active worker cleanly. These timings characterize that host,
not the Windows reference PC. See `docs/PHYSICS_RENDER_COUPLING.md` for the
contracts and `docs/STEP7_VALIDATION.md` for the short hardware check.

## Step 8 output

Step 8 replaces the single implicit initial state with an explicit reproducible
experiment contract:

- `ExperimentConfig` atomically identifies scenario, Barnes-Hut particle count,
  and visible random seed;
- the catalogue supplies spiral, uniform disk, ring, sphere, frontal encounter,
  oblique encounter, bound random cloud, and total-chaos initial conditions;
- every generator is deterministic, finite, mass-centred, and corrected to zero
  bulk momentum before it reaches a solver;
- `Appliquer et recommencer` uses the displayed configuration while `Changer
  la graine` changes and displays only the seed;
- Barnes-Hut accepts 100 to 50,000 particles and the UI gives an indicative
  relative `N log N` workload before launch;
- the exact comparison still enforces a 1,000-body ceiling internally and
  returning to Barnes-Hut restores the requested count, scenario, seed, pause,
  and speed;
- the GPU buffer can resize in place, and generation changes rebuild visual
  attributes even when the particle count stays constant.

The automated suite validates every scenario both statically and through real
Barnes-Hut/leapfrog advances. See `docs/INITIAL_SCENARIOS.md` for the physical
meaning and caveats, and `docs/STEP8_VALIDATION.md` for the Windows check.

## Step 9 output

Step 9 adds a linear-time observation layer beside, never inside, the numerical
solver:

- distance, speed, origin-component, approximate-energy, and ejection colour
  modes rebuild presentation attributes from immutable worker snapshots;
- centre of mass, median radius, maximum speed, estimated energy and drift, and
  linked/ejected counts are available without an additional pairwise pass;
- an ejection requires all three conditions: beyond a boundary derived from the
  initial 95th-percentile radius, outward radial motion, and positive estimated
  orbital energy; ejected particles remain in the physical state;
- the energy and ejection calculations use an explicit spherical-monopole
  approximation plus supported analytic Plummer fields, and are labelled as
  estimates rather than exact invariants;
- perspective, top, and profile views preserve zoom and focus, while an optional
  marker exposes centre-of-mass drift;
- `Space`, `R`, `F`, `Escape`, and `Tab` provide edge-triggered shortcuts that do
  not fire while a text field captures the keyboard;
- requested/effective speed exposes the live compute ceiling instead of implying
  that the speed slider can outrun the solver;
- the panel prioritises controls, observation, and experiment setup; performance
  and technical sections are collapsed by default.

See `docs/STEP9_VALIDATION.md` for the short Windows visual and interaction gate.

## Validation cadence

The owner receives a testable build at the points where local hardware or user
feel matters:

- after step 2: installation and launch workflow;
- after step 3: graphics, camera, DPI, and visual shell;
- after steps 4-5: reference physics and rotating galaxy;
- after step 6: 10,000-particle performance and approximation quality;
- after step 7: physical motion, worker responsiveness, and optional exact comparison;
- after step 8: scenario selection, reproducibility, and particle-count changes;
- after step 9: physical observability and appearance;
- after step 10: timeline correctness, memory limits, and accelerated replay;
- after step 11: particle selection, trails, and follow-camera feel;
- after step 12: merger conservation and collision-heavy scenarios;
- after step 13: release candidate.

Automated checks are run before every handoff. Manual checks are short and
specific; they do not replace tests that can be automated.

## Decision gates

### Graphics gate (step 3)

Keep the GLFW / Dear ImGui Bundle / ModernGL stack only if the integrated smoke
application starts reliably on the reference PC, handles resize/DPI correctly,
and renders the synthetic 10,000-particle field within budget.

### Barnes-Hut gate (step 6)

Barnes-Hut becomes the default only if it meets both the documented error
threshold and a measured performance advantage over the exact reference at
relevant particle counts.

This gate passed at theta 0.7: both seeded accuracy sets are inside budget and
the same-host 10,000-particle benchmark is 26.92x faster than the exact solver.

### Backend gate (before final delivery)

Keep Python + Numba when V1 budgets are met. Move only the measured hot boundary
to GPU/C++/Rust if it is not. A full rewrite is not the default outcome.

## Change control

New features first enter `SPECIFICATION.md` as either V1 scope or post-V1 scope.
Changes to an accepted architectural decision require a superseding ADR with
measurements or a concrete compatibility problem. This keeps the project
adaptable without letting implementation choices drift from one step to another.
