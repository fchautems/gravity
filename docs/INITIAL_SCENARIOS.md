# Initial-condition laboratory — step 8

Step 8 turns the single published galaxy into a reproducible initial-condition
laboratory. The UI prepares a complete experiment and sends it to the physics
worker as one immutable value; individual fields are never changed inside a
running state.

## Reproducible experiment contract

An experiment is identified by exactly three public values:

- scenario kind;
- Barnes-Hut particle count;
- random seed.

`Appliquer et recommencer` regenerates all positions, velocities, masses, IDs,
component labels, analytic fields, and integrator buffers at a worker safe
point. Applying the same three values recreates the same initial arrays.
`Changer la graine` prepares a different seed without restarting; the change
takes effect only after `Appliquer et recommencer`.

The supported Barnes-Hut range is 100 to 50,000 particles. Both dual-galaxy
scenarios require at least 200 so each side can reuse a valid 100-body galaxy.
The advanced exact backend remains capped at 1,000 bodies. Switching to exact
does not forget the requested Barnes-Hut count; returning restores it.

## Catalogue

| Scenario | Initial positions | Initial velocities | External field |
|---|---|---|---|
| Galaxie spirale | Exponential disk, Hernquist bulge, central body | Coherent rotation curve with small seeded dispersion | Centred Plummer halo |
| Disque uniforme | Uniform surface-density disk with thin vertical scatter | Circular rotation from live enclosed mass and halo | Centred Plummer halo |
| Anneau | Narrow clipped radial band | Circular rotation with a seeded small dispersion | Centred Plummer halo |
| Sphère gravitationnelle | Uniform-volume sphere | Isotropic near-virial random velocities | None |
| Collision frontale | Two compact, self-gravitating spiral galaxies | Opposed centre velocities | None |
| Collision oblique | Two translated and differently tilted galaxies | Offset opposed centre velocities | None |
| Aléatoire lié | Uniform random cube | Low isotropic near-virial velocities | None |
| Chaos total | Same random cube family | Velocities sampled around the escape-speed scale | None |

Every generator removes mass-weighted centre-of-mass position and bulk velocity
before constructing `ParticleState`. Fixed seeds produce exact initial arrays in
the automated suite. Different seeds change every catalogue entry.

`Aléatoire lié` is designed to remain globally bound often enough to show
collapse, clumps, streams, and relaxation. It is not promised to become a
realistic spiral galaxy. `Chaos total` intentionally makes no stability promise:
particles can collapse, cross, or escape.

## What “collision” means here

The two-galaxy presets are collisionless N-body encounters. Their gravitational
fields interact and can form bridges, tails, mixing, and ejections. Individual
particles still have no physical radius, bounce, or merge rule; they may pass
through one another. Finite-size particle collision and merger physics remains a
later independent milestone.

## Performance indication

The panel shows a relative Barnes-Hut workload estimate using
`N log2(N) / (10,000 log2(10,000))`. This is an ordering aid, not a milliseconds
promise: tree shape, CPU, thread count, scenario evolution, and JIT warm-up all
affect real time. Live `Physique : ... ms / pas` remains the measured value.

## Rendering regeneration

A generation change rebuilds visual attributes even when the new scenario has
the same particle count. Ordinary physics snapshots update positions only. This
prevents a new ring, sphere, or collision from inheriting the previous
scenario's initial radial colour field while keeping the normal upload path
small. Step 9 will replace this single presentation rule with selectable colour
metrics.
