# Architecture decision records

Architecture decision records (ADRs) preserve the reasoning behind choices that
affect several implementation steps.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-python-and-compiled-kernels.md) | Python orchestrates; NumPy and Numba execute CPU physics | Accepted |
| [0002](0002-desktop-graphics-stack.md) | GLFW + ModernGL + Dear ImGui Bundle, targeting OpenGL 3.3 | Accepted, compatibility-gated |
| [0003](0003-numerical-model.md) | Softened Newtonian gravity, exact reference, Barnes-Hut, leapfrog | Accepted |
| [0004](0004-state-and-concurrency.md) | Contiguous array state with single-writer physics and render snapshots | Accepted |

An accepted ADR is not permanent. Replacing it requires a new ADR that links to
the old one and records the evidence for the change.

