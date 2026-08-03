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

