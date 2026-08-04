# ADR 0001: Python with compiled numerical kernels

- Status: Accepted
- Date: 2026-08-03

## Context

The original project was easy to express in Python but slow because it used many
Python objects, recursive Python traversal, and per-particle work in the render
layer. Rewriting everything in C++ or Rust would raise complexity before the
actual algorithm and performance limits are known.

The V1 target is 10,000 particles, not millions, and the project owner already
works comfortably in Python.

## Decision

Use 64-bit CPython 3.12 as the supported V1 runtime.

- Python owns configuration, orchestration, scenarios, UI, diagnostics, and
  tests.
- NumPy owns contiguous particle arrays.
- Numba `nopython` kernels own intensive CPU loops.
- Python object graphs and Python recursion are excluded from hot paths.
- Versions are pinned and installed into a repository-local virtual environment.

## Consequences

This keeps development and numerical testing fast while allowing native-speed
loops. JIT compilation introduces a first-use delay, which the installer or app
must warm up and explain.

Numba-friendly flat data structures influence the Barnes-Hut implementation.
That is an intentional performance design, not a leak of UI concerns into
physics.

The backend boundary remains replaceable. GPU, C++, or Rust work is considered
only after reproducible release benchmarks show a missed V1 goal.

## Rejected alternatives

- Pure Python: cannot meet the target predictably in hot loops.
- NumPy broadcasting for full pair matrices: creates `O(N^2)` memory pressure.
- Immediate full C++/Rust rewrite: higher cost before measured need.
- CUDA as the first backend: ties the first working version to one GPU stack and
  skips the exact CPU reference.
