# Exact physics reference — step 4

Step 4 establishes a small-system numerical oracle before any Barnes-Hut
approximation is introduced. It does not yet drive the step-3 visual galaxy.
That separation is intentional: rendering cannot make an incorrect trajectory
look correct, and an approximate solver must later be compared against an
independent reference.

## Implemented model

- dimensionless internal units with `G = 1`;
- three-dimensional Plummer-softened Newtonian gravity;
- one symmetric evaluation per unordered particle pair;
- fixed-step kick-drift-kick leapfrog integration;
- physics arrays stored as C-contiguous `float64` structure-of-arrays data;
- unique `uint64` particle identifiers;
- compiled Numba force and potential-energy kernels without an `N x N`
  temporary matrix.

For particles `i` and `j`, the direct solver applies:

```text
a_i += m_j (r_j - r_i) / (|r_j - r_i|² + epsilon²)^(3/2)
a_j -= m_i (r_j - r_i) / (|r_j - r_i|² + epsilon²)^(3/2)
```

Evaluating both contributions together makes conservation errors easy to
detect and avoids calculating the same pair twice. Time and memory complexity
are respectively `O(N²)` and `O(N)`. This is a correctness engine for small
systems, not the future 10,000-particle interactive backend.

## State and validation boundary

`ParticleState` owns positions, velocities, accelerations, masses, and IDs as
whole arrays. It rejects:

- empty or mismatched arrays;
- a dtype other than the documented `float64` / `uint64` contract;
- non-contiguous mutable state;
- NaN or infinity;
- zero or negative mass;
- duplicate IDs;
- invalid time or step counters.

The solver additionally validates a positive, representable softening length
and prevents its output buffer from overlapping its inputs. The integrator
rejects a non-positive or non-finite fixed time step.

## Documented circular-orbit test

The long-run gate uses two masses `0.4` and `0.6`, unit separation, and
softening `epsilon = 0.02`. Their analytic softened circular frequency is:

```text
omega = sqrt((m1 + m2) / (r² + epsilon²)^(3/2))
```

The integration step is one orbital period divided by 256. The ordinary test
suite advances 100 complete periods (25,600 fixed steps) and checks:

| Measure | Required | Observed in the step-4 gate |
|---|---:|---:|
| Relative energy drift | `< 1e-3` | `2.67e-9` |
| Centre-of-mass drift | `<= 1e-9` | `3.76e-13` |
| Momentum drift | `<= 1e-12` | `1.53e-15` |
| Final separation | within `0.2%` of `1.0` | `1.0000089` |

The observed values document the validation run; the pass/fail limits are the
portable contract. The test also checks the analytic two-body acceleration,
force antisymmetry for unequal seeded masses, coincident softened particles,
a force-free trajectory, invariants with closed-form values, and equality of
the compiled kernels with their Python reference execution.

## Public components

- `gravity.core.state.ParticleState`: validated mutable physics state;
- `gravity.physics.ExactGravitySolver`: direct symmetric acceleration solver;
- `gravity.physics.LeapfrogIntegrator`: fixed-step integration;
- `gravity.physics.invariants`: mass, centre of mass, momentum, angular
  momentum, kinetic energy, softened potential energy, and total energy.

Step 5 will build physically coherent galactic initial conditions with these
contracts. Step 6 will compare Barnes-Hut accelerations directly against this
exact solver before the approximate engine can become interactive.
