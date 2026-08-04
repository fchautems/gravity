# Step-8 Windows validation

This check validates the new experiment controls on the real Windows/OpenGL
target. It should take about five minutes.

## Start

1. Update the repository.
2. Run `INSTALLER.bat` once.
3. Start `LANCER_GRAVITY.bat`.

The panel should say `Jalon 8 · laboratoire gravitationnel` and start directly
on `Galaxie spirale`, 10,000 particles, seed `20260803`, and Barnes-Hut.

## Reproducibility

1. Pause the simulation immediately.
2. Select `Anneau`, 5,000 particles, and seed `1234`.
3. Click `Lancer cette expérience` and note the initial pattern.
4. Advance one step, then click `Recommencer à l’identique`.
5. Confirm the original pattern returns.
6. Click `Nouveau tirage` and confirm the displayed seed and pattern both change.

## Catalogue

Briefly launch each configuration:

- `Galaxie spirale`;
- `Disque uniforme`;
- `Anneau`;
- `Sphère gravitationnelle`;
- `Collision frontale`;
- `Collision oblique`;
- `Aléatoire lié`;
- `Chaos total`.

Confirm the viewport, camera, pause, and panel stay responsive. The two collision
presets should clearly begin as two separated objects. The random presets need
not settle into a spiral; their unpredictable evolution is intentional.

## Counts and exact guard

Test Barnes-Hut at 1,000 and 25,000 particles. The GPU buffer and displayed
count should change without restarting the application. Open `Physique avancée`
on the 25,000-body experiment and activate exact mode: it must show 1,000
particles maximum. Return to Barnes-Hut and confirm 25,000 returns with the same
scenario and seed.

Useful feedback is a screenshot of the initial-condition section plus the FPS,
physics milliseconds per step, selected scenario, and particle count.
