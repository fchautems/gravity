# Barnes-Hut self-gravity — step 6

Step 6 replaces all-pairs force evaluation at interactive particle counts with
a measured three-dimensional Barnes-Hut approximation. The exact step-4 solver
remains the numerical oracle and is still used for small systems, regression
tests, and every accuracy report.

Step 7 now connects this solver to the OpenGL particles through the fixed-step
worker and immutable snapshot exchange. Barnes-Hut is the interactive default;
the exact engine remains an explicitly selected small-system reference.

## Numerical model

Both solvers evaluate the same softened Newtonian acceleration with `G = 1`:

\[
\mathbf a_i = \sum_{j \ne i}
    m_j\frac{\mathbf x_j-\mathbf x_i}
    {\left(\lVert\mathbf x_j-\mathbf x_i\rVert^2+\epsilon^2\right)^{3/2}}.
\]

Barnes-Hut changes only how distant sources are represented. A sufficiently
distant octree node contributes its total mass at its centre of mass; nearby
nodes are opened until individual leaf particles are evaluated directly. No
quadrupole or higher multipole is used in V1.

The opening test is

\[
\frac{s}{d} < \theta,
\]

where `s` is the node cube width, `d` is the unsoftened distance to its centre
of mass, and the validated default is `theta = 0.7`. Smaller theta values open
more nodes and trade speed for precision. Solver configuration is immutable
after validation; changing a physical parameter creates a new solver instance
instead of silently changing a running calculation.

## Flat octree

The tree contains no recursive Python node objects. Its complete state is held
in C-contiguous arrays:

| Array | Per-node content |
|---|---|
| `centers`, `half_sizes` | cubic spatial bounds |
| `children` | eight `int32` child indices, `-1` when absent |
| `starts`, `counts` | nested range in one particle permutation |
| `depths` | depth used by the subdivision guard |
| `masses`, `centers_of_mass` | bottom-up monopole aggregate |

`particle_order` stores every particle exactly once and `inverse_order` maps a
particle back to its nested tree range. The latter lets traversal prove whether
a node contains the target particle without searching its contents. A node
containing the target is always opened, so its own mass can never be accepted
as a distant source.

Construction is deterministic:

1. create a cubic root around the complete current position range;
2. partition each occupied node range into its non-empty octants;
3. stop at eight particles per leaf or depth 32 by default;
4. aggregate mass and centre of mass from leaves to root;
5. rebuild from current positions for every force evaluation.

Storage grows and the build restarts if an adversarial distribution exceeds
the initial capacity estimate. Coincident particles terminate at the depth
limit and remain in one direct leaf instead of causing infinite subdivision.

## Compiled traversal

The force traversal is iterative and Numba-compiled. Below 2,048 particles it
uses one sequential kernel to avoid parallel scheduling overhead. At and above
that threshold, targets are independent `prange` iterations. Each target keeps
a bounded explicit stack; no Python recursion or object allocation occurs per
tree node.

`BarnesHutStats` records separately:

- tree-build time;
- force-traversal time;
- node, leaf, and maximum-depth counts;
- accepted aggregate-node interactions;
- direct leaf-particle interactions.

The benchmark's total time is the complete public `compute` call, including
validation and instrumentation; it is therefore directly comparable with the
timed exact `compute` call. Tree and force columns remain the internal split.

The installer warms both the sequential and parallel kernels so first use in
the interactive worker does not look like an application freeze.

## Accuracy gate

For each reference acceleration above the near-zero floor,

\[
e_i = \frac{\lVert\mathbf a_i^{BH}-\mathbf a_i^{exact}\rVert}
            {\lVert\mathbf a_i^{exact}\rVert}.
\]

The floor is `max(float64.tiny, 1e-12 * max(reference norm))`. Samples below it
are excluded from relative ratios and their absolute error is reported
separately. The V1 limits are median error at most 2% and 95th-percentile error
at most 5%.

| Seeded validation set | Particles | Median | 95th percentile | Result |
|---|---:|---:|---:|---|
| Spiral galaxy, seed 1234 | 512 | 1.142% | 3.125% | Pass |
| Three-cluster cloud, seed 86753090 | 384 | 0.036% | 0.789% | Pass |

Tests also prove exact one- and two-body results, deterministic topology,
bottom-up mass aggregates, immutable tree arrays, bounded coincident-particle
behaviour, and bitwise equality between sequential and parallel traversals.

## Reproducible benchmark

Run after `INSTALLER.bat`:

```text
.venv\Scripts\python.exe benchmarks\step6_barnes_hut.py
```

Use `--json` for machine-readable output. The committed baseline used 64-bit
Python 3.12.13, NumPy 2.4.6, Numba 0.66.0, nine Numba threads, theta 0.7, seed
20260806, and 21 warmed repetitions. It is a Linux-container measurement,
not a claimed Windows hardware constant.

| Particles | Tree median | Force median | Total median | Exact median | Speedup | Median error | P95 error |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 0.059 ms | 0.056 ms | 0.140 ms | 0.041 ms | 0.29x | 0.417% | 2.346% |
| 1,000 | 0.125 ms | 2.292 ms | 2.477 ms | 3.097 ms | 1.25x | 1.279% | 3.142% |
| 10,000 | 1.073 ms | 10.063 ms | 11.509 ms | 309.888 ms | 26.92x | 1.291% | 3.294% |
| 50,000 | 6.102 ms | 61.834 ms | 68.735 ms | not run | — | — | — |

The tree arrays occupy about 0.50 MiB at 10,000 particles and 2.56 MiB at
50,000. The decisive gate is the same-host 10,000-particle comparison: the
approximation is well inside its error budget and more than ten times faster
than the exact oracle. Step 7's same-container coupled smoke measured 13.35 ms
for its last 10,000-body step while the renderer consumed snapshots
independently. Absolute Windows throughput remains part of the target-PC
checklist because thread scheduling and CPU performance differ by machine.

## Public components

- `gravity.physics.BarnesHutSolver`: solver-compatible approximation;
- `gravity.physics.BarnesHutStats`: last-run structural and timing evidence;
- `gravity.physics.FlatOctree`: immutable validated flat structure;
- `gravity.physics.build_octree`: deterministic tree construction for tests;
- `gravity.diagnostics.compare_accelerations`: reusable exact-versus-approximate
  error report.
