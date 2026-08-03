# ADR 0004: Array state and snapshot concurrency

- Status: Accepted
- Date: 2026-08-03

## Context

The UI must remain responsive while the CPU constructs an octree and computes
forces. Sharing mutable NumPy arrays directly with the renderer risks torn
frames and data races. Giving each particle a Python object recreates the main
cost of the historical implementation.

## Decision

- Store particle properties in a small set of typed, contiguous arrays.
- Make the physics worker the sole writer of live simulation state.
- Keep OpenGL and UI work on the main thread.
- Exchange immutable render snapshots through a bounded double buffer.
- Exchange user actions through explicit validated command values.
- Allow stale render snapshots to be dropped; never drop physics steps or mutate
  live state from the renderer.

## Consequences

The render layer receives a coherent frame and cannot corrupt physics. Copying
10,000 positions to `float32` is inexpensive compared with force evaluation and
makes ownership obvious.

Reset, regeneration, and shutdown need explicit worker acknowledgements. These
paths are integration-tested because they are common sources of race conditions.

The same contracts work synchronously in early physics tests, so concurrency is
introduced only when the components are individually reliable.

## Rejected alternatives

- Shared mutable arrays with informal locking: too easy to render partial state.
- One process per subsystem: unnecessary serialization complexity for V1.
- OpenGL work on a background thread: conflicts with context ownership and
  window-system expectations.
- Unbounded queues: allow latency and memory to grow during slow rendering.

