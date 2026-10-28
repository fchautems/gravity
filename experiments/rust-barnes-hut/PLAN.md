# Rust Barnes–Hut performance experiment

This isolated branch tests whether a Rust native kernel improves on the existing NumPy/Numba Barnes–Hut engine **without compromising numerical accuracy**. Do not replace the production backend before evidence.

## Baseline
- Existing benchmark: `benchmarks/step6_barnes_hut.py --json`
- Existing sample: `benchmarks/results/step6_linux_x86_64.json`
- Use identical seeded configurations at 1,000, 5,000 and 10,000 particles.
- Record machine, OS, Python/Rust/compiler versions, CPU threads, warm-up, timings (median/p95), tree build, force traversal, integration, peak memory, and numerical error against exact reference where feasible.
- Ensure comparable Barnes–Hut opening angle, softening, integration, and force calculations.

## Rust prototype
- Keep Python UI and orchestration unchanged.
- Prototype only the computational hot path behind a clearly defined array-based interface; avoid per-particle Python/Rust calls.
- Benchmark Rust core separately from Python FFI and copy overhead.
- Run existing correctness tests; do not claim speedup from unmatched accuracy or cold JIT timings.

## Acceptance
- Compare Numba and Rust at the same accuracy and report end-to-end performance.
- Retain Rust only if measured improvement justifies complexity and portability cost.
- No changes to `master` until explicitly reviewed.
