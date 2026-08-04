# Benchmarks

Benchmarks report, at minimum:

- machine and software environment;
- seed and complete simulation configuration;
- warm-up state;
- particle count;
- tree-build, force, integration, snapshot upload, and render timings;
- memory usage;
- Barnes-Hut error against the exact solver where feasible;
- median and tail measurements rather than a single best run.

Benchmark code arrives with the component being measured. It remains separate
from ordinary unit tests so noisy timing does not create flaky correctness
failures.

Step 6 adds `step6_barnes_hut.py`. It warms the compiled paths, measures tree
construction, force traversal, total Barnes-Hut time, exact time where feasible,
tree memory, interaction counts, and exact-force error. Run it after installation:

```text
.venv\Scripts\python.exe benchmarks\step6_barnes_hut.py --json
```

The committed `results/step6_linux_x86_64.json` is evidence from one identified
environment, not a cross-machine performance assertion. Correctness tests use
the same deterministic error report but never fail on wall-clock timing.
