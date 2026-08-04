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

## Step-4 implementation evidence

The direct symmetric solver, strict `float64` particle state, softened-energy
diagnostics, and kick-drift-kick integrator were implemented without fast-math.
The documented 100-orbit circular binary produced relative energy drift
`2.67e-9` and centre-of-mass drift `3.76e-13`; the full parameters and portable
thresholds are recorded in `../PHYSICS_REFERENCE.md`.

## Step-5 implementation evidence

The default live disk, bulge, and central mass now receive initial velocities
from a documented smooth enclosed-mass curve. The Plummer halo remains a
separate analytic field and is composed only after self-gravity. The seeded
240-particle exact gate retains a median radius ratio of `0.996` after 200 steps
while advancing a median `0.513` radians. Model assumptions and the complete
distribution evidence are recorded in `../GALAXY_MODEL.md`.

## Rejected alternatives

- Explicit Euler: unacceptable energy behaviour for orbits.
- Barnes-Hut without an exact reference: approximation errors would be hard to
  distinguish from integrator or tree bugs.
- Adaptive time step in V1: adds synchronization and conservation complexity.
- Direct summation as the only engine: cannot scale to the default target.
