# ADR 0003: Numerical model

- Status: Accepted
- Date: 2026-08-03

## Context

An approximate large-N solver is hard to validate by visual inspection. The
original project also used a simple Euler update, which can inject or remove
energy from orbital systems.

## Decision

- Use three-dimensional softened Newtonian gravity with dimensionless `G = 1`.
- Use kick-drift-kick leapfrog with a fixed simulation step.
- Implement a symmetric direct solver as the small-N reference.
- Implement a flat-array Barnes-Hut octree as the V1 interactive solver.
- Measure Barnes-Hut acceleration error against the direct solver on seeded
  distributions before making it the default.
- Keep analytic background galaxy potentials separate from self-gravity.

## Consequences

The exact solver provides a test oracle, even though it is not the large-N
engine. Leapfrog gives much better long-term orbital behaviour than explicit
Euler while remaining simple and reversible at fixed step.

Softening, time step, and Barnes-Hut theta are part of a reproducible simulation
configuration. They cannot change silently with frame rate or visual preset.

An analytic halo may be used to produce a stable V1 galaxy, but results must
state that this is a modelled external potential, not a fully self-consistent
dark-matter particle simulation.

## Rejected alternatives

- Explicit Euler: unacceptable energy behaviour for orbits.
- Barnes-Hut without an exact reference: approximation errors would be hard to
  distinguish from integrator or tree bugs.
- Adaptive time step in V1: adds synchronization and conservation complexity.
- Direct summation as the only engine: cannot scale to the default target.

