# Step 9 Windows validation

This short check validates the parts that automated headless tests cannot prove:
font rendering, colour readability, fullscreen behaviour, and the visual feel of
the canonical camera views.

## Start

1. Run `INSTALLER.bat`, then `LANCER_GRAVITY.bat`.
2. Confirm the initial galaxy is an immobile preview labelled `Pret`.
3. Change the scenario, particle count, and seed; the preview must regenerate
   without beginning the simulation.
4. Press `Demarrer`, then `Pause`, `Reprendre`, and `Stop`. `Stop` must restore
   the selected experiment at time zero without losing its configuration.
5. Confirm the complete primary panel and its bottom data dock fit without a
   vertical scrollbar, including in fullscreen.

## Observation

1. Pause with `Space` and cycle through all five colour modes.
2. Confirm every mode has a visible legend matching the rendered palette.
3. Confirm distance, speed, component, and energy produce visibly different
   maps rather than variations of the same blue.
4. In `Liees / ejectees`, confirm ejected particles are pink-red when any appear.
5. Enable the centre-of-mass marker and confirm the bright green marker appears
   near the physical centre.
6. Open `Statistiques`, `Performances`, and `Technique` from the fixed bottom
   dock. Each drawer must fit without scrolling and close with a second click or `x`.
7. Confirm all displayed physical values remain finite.

The energy is intentionally labelled `estimee`. The ejection count is an
observational classification; particles are not removed from the solver.

## Camera and shortcuts

1. Select Perspective, Dessus, and Profil; zoom must remain unchanged.
2. Orbit manually, then press `R`; the camera must return to perspective.
3. Press `F`; the window must fill the primary monitor. Press `Escape`; the
   previous position and size must return.
4. Press `Tab` twice; the control panel must disappear and return.
5. Click in the seed field and type: global shortcuts must not trigger while the
   field owns keyboard input.

## Technical comparison

1. Open the `Technique` drawer and confirm Barnes-Hut is the normal engine.
2. Launch the exact O(N2) comparison and confirm the explicit 1'000-particle
   limit remains visible.
3. Return to Barnes-Hut and confirm the selected scenario, seed, particle count,
   pause state, and speed are restored.

## Compute ceiling

1. Launch 50'000 particles and raise requested speed to 2.5x.
2. Confirm the panel distinguishes requested and effective speed.
3. The renderer should remain responsive even when effective speed is below the
   request.
