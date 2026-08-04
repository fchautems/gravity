# Step-7 Windows validation

This is the first manual test where the galaxy visible on screen is genuinely
physical. It should take about three minutes.

## Before launching

1. Update or download the repository.
2. Run `INSTALLER.bat` once, even if step 6 was already installed.
3. Start `LANCER_GRAVITY.bat`.

## Normal Barnes-Hut mode

Confirm the following:

- the panel says `Jalon 7 · gravitation réelle`;
- 10,000 particles are visible and `Moteur : Barnes–Hut` appears only after
  opening `Physique avancée`;
- the galaxy moves while orbit, pan, zoom, resize, and the FPS overlay remain
  responsive;
- `Pause` freezes the physical positions;
- while paused, `Avancer d’un pas` changes them once;
- `Recommencer` returns to the original seeded shape;
- the physical milliseconds per step remain finite and continue updating.

## Optional exact comparison

Open `Physique avancée` and click `Tester le moteur exact · 1’000 particules`.
This is optional and intentionally not part of normal use.

Confirm that the panel changes to `MODE DE COMPARAISON`, shows exactly 1,000
particles, and stays responsive. Click `Revenir à Barnes–Hut · 10’000
particules`; the default count and backend must return. Pause state should be
preserved through both changes.

## Useful report

If possible, send one screenshot in Barnes-Hut mode after a few seconds. The
useful values are GPU name, FPS, physics milliseconds per step, particle count,
and whether the overall galactic shape remains coherent. If anything fails,
also send the newest file from `%LOCALAPPDATA%\Gravity\logs`.

