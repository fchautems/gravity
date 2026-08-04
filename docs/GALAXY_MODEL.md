# V1 galaxy initial conditions — step 5

Step 5 creates the reproducible physical state that the exact and Barnes-Hut
solvers consume. It deliberately remains independent from the
step-3 renderer: `LANCER_GRAVITY.bat` still displays the synthetic visual field
until the physics worker and snapshot exchange are connected in step 7.

The goal is a coherent rotating initial condition, not a claim that the V1 is
a scientific Milky Way formation model.

## Default configuration

The default seed is `20260803`. The generator creates exactly 10,000 live
particles:

| Component | Particles | Live mass | Spatial model |
|---|---:|---:|---|
| Stellar disk | 8,399 | 0.60 | Truncated exponential disk with four seeded spiral overdensities |
| Central bulge | 1,600 | 0.20 | Truncated spherical Hernquist profile |
| Central mass | 1 | 0.02 | Live softened point mass at the corrected origin |
| Analytic halo | no particles | 1.20 asymptotic | External Plummer potential, scale radius 6.0 |

All values use the dimensionless internal units established in ADR 0003, with
`G = 1`. The default disk scale length is `2.05`, outer radius `10.8`, scale
height `0.12`, softening `0.08`, and fixed time step `0.02`.

The halo is not represented by dark-matter particles. It is an explicitly
modelled external potential and remains separate from particle self-gravity in
both code and tests.

## Spatial sampling

### Exponential disk

The disk surface density follows:

```text
Sigma(R) proportional to exp(-R / Rd)
```

The radial probability therefore includes the cylindrical area term. Before
normalization at the configured truncation radius, its cumulative distribution
is:

```text
F(R) = 1 - exp(-R / Rd) * (1 + R / Rd)
```

The code inverts the truncated CDF with a fixed-count bisection, avoiding an
unbounded rejection loop and preserving deterministic random-number use.
Vertical positions use a narrow seeded Gaussian distribution.

The four arms are angular overdensities applied after radial sampling. They do
not alter the exponential radial CDF. They are an initial visual structure, not
a stationary density-wave solution; differential rotation may shear them over
time.

### Bulge

The spherical bulge uses the Hernquist cumulative mass fraction:

```text
F(r) = r^2 / (r + a)^2
```

It is sampled directly, normalized at the configured outer radius, with
isotropic directions. The bulge is pressure-supported by seeded isotropic
velocities rather than being forced into the thin disk's rotation.

## Analytic halo and initial rotation curve

The Plummer halo acceleration is:

```text
a(r) = -M_h * r / (|r|^2 + a_h^2)^(3/2)
```

and its equivalent enclosed mass is:

```text
M_h(<r) = M_h * r^3 / (r^2 + a_h^2)^(3/2)
```

The generator builds a smooth enclosed-mass curve from:

- the truncated exponential disk;
- the truncated Hernquist bulge;
- the softened central mass;
- the Plummer halo.

Disk particles receive the corresponding approximate circular speed:

```text
v_c(r) = sqrt(M_total(<r) / r)
```

plus small, seeded radial, tangential, and vertical dispersions. This uses a
spherical enclosed-mass approximation for initialization; the live flattened
disk is subsequently evolved by the actual particle solver. It is intentionally
simple, documented, and testable rather than presented as an exact equilibrium
distribution function.

After generation, the live non-central particles are translated so that the
central particle remains at the origin while the complete mass-weighted centre
of mass is zero. Their bulk velocity is removed in the same way. Particle order
is then deterministically shuffled to avoid grouping components in solver
input.

## Validation gate

The ordinary suite checks exact reproduction, array contracts, component
counts, mass totals, distribution statistics, the rotation curve, the analytic
halo, global centring, and a short dynamic run.

Observed for the documented 10,000-particle seed:

| Measure | Observed |
|---|---:|
| Centre-of-mass norm | `1.22e-16` |
| Total-momentum norm | `1.29e-17` |
| Disk particles rotating in the configured direction | `100%` |
| Median absolute radial/tangential speed ratio | `0.0242` |
| Disk radial 10% / 50% / 90% quantiles | `1.036 / 3.332 / 7.329` |
| Bulge median spherical radius | `0.931` |

The dynamic gate uses 240 particles, seed `1234`, an axisymmetric disk, the
exact self-gravity solver, the analytic halo, and 200 leapfrog steps. Its median
disk radius finishes at `0.996` of the initial value while the median angular
travel is `0.513` radians. The 10% and 90% radius ratios are `0.882` and `1.101`.
This demonstrates coherent initial rotation without prompt collapse; long-run
10,000-particle stability remains a Barnes-Hut and coupling validation task.

## Public components

- `gravity.scenarios.GalaxyConfig`: immutable, validated scenario parameters;
- `gravity.scenarios.generate_spiral_galaxy`: deterministic initial-state
  factory;
- `gravity.scenarios.GalaxyInitialConditions`: particle state, component
  labels, configuration, and smooth mass model;
- `gravity.scenarios.GalaxyMassModel`: documented enclosed-mass rotation curve;
- `gravity.physics.PlummerPotential`: analytic external halo field;
- `gravity.physics.CompositeGravitySolver`: explicit composition of
  self-gravity and external fields.

Step 6 implements and compares Barnes-Hut against the exact self-gravity solver.
The analytic halo is added identically after either self-gravity backend, so it
does not contaminate that accuracy comparison. See `BARNES_HUT.md` for the
measured gate.
