# Gravity implementation roadmap

This roadmap turns the V1 specification into independently verifiable gates.
Only one gate is implemented at a time. A later gate may not hide a failure in an
earlier one.

## Progress

| Step | Deliverable | Exit criterion | Status |
|---:|---|---|---|
| 1 | V1 specification and architecture | Scope, budgets, module boundaries, numerical model, and test strategy are recorded; source package skeleton exists. | **Complete** |
| 2 | Reproducible setup and double-click launchers | Clean Windows setup, launch, and test smoke path work without a typed command; failures produce useful output. | Next |
| 3 | Graphics shell | Styled window, UI panel, camera, and a single GPU draw render 10,000 synthetic points smoothly. | Planned |
| 4 | Exact physics reference | Direct solver and leapfrog pass two-body, conservation, symmetry, and long-run tests. | Planned |
| 5 | Galaxy generator | A seeded disk/bulge/halo configuration rotates coherently and passes distribution tests. | Planned |
| 6 | Barnes-Hut | Flat octree passes structure tests, meets error budgets against exact forces, and demonstrates measured speedup. | Planned |
| 7 | Physics/render coupling | Fixed-step worker, command queue, snapshots, pause/step/reset, and clean shutdown are reliable. | Planned |
| 8 | Complete user controls | Basic/advanced controls, validation, presets, settings persistence, and French help text are usable. | Planned |
| 9 | Visual quality | Colour, point sprites, glow/trails, fullscreen, and screenshots are polished and individually measurable. | Planned |
| 10 | Robustness | Edge cases, paths, DPI, missing dependencies, invalid settings, restart loops, and a 30-minute soak pass. | Planned |
| 11 | Benchmark and optimize | Timings, memory, and accuracy are separated; bottlenecks are optimized from evidence; backend decision is recorded. | Planned |
| 12 | V1 delivery | Documentation, versioning, scenarios, test report, benchmark report, and final Windows workflow match the release. | Planned |

## Step 1 output

Step 1 creates no simulation placeholder. Its durable output is:

- `docs/SPECIFICATION.md`: what V1 must do and how success is measured;
- `docs/ARCHITECTURE.md`: how the system is separated and how data moves;
- `docs/adr/`: decisions that should not drift silently;
- `src/gravity/`: package boundaries with no fake implementation;
- `tests/README.md` and `benchmarks/README.md`: verification rules.

## Validation cadence

The owner receives a testable build at the points where local hardware or user
feel matters:

- after step 2: installation and launch workflow;
- after step 3: graphics, camera, DPI, and visual shell;
- after steps 4-5: reference physics and rotating galaxy;
- after step 6: 10,000-particle performance and approximation quality;
- after steps 7-9: complete interaction and appearance;
- after steps 10-12: release candidate.

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

### Backend gate (step 11)

Keep Python + Numba when V1 budgets are met. Move only the measured hot boundary
to GPU/C++/Rust if it is not. A full rewrite is not the default outcome.

## Change control

New features first enter `SPECIFICATION.md` as either V1 scope or post-V1 scope.
Changes to an accepted architectural decision require a superseding ADR with
measurements or a concrete compatibility problem. This keeps the project
adaptable without letting implementation choices drift from one step to another.

