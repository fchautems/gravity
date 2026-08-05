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

1. Pause with `Space` and cycle through all six colour modes.
2. Confirm every mode has a visible legend matching the rendered palette.
3. Confirm distance, speed, mass, object origin, and energy produce visibly different
   maps rather than variations of the same blue.
4. On a collision, select `Objet d'origine`: the two starting galaxies must
   have two immediately distinguishable colours, retained as they mix.
5. Select `Masse`: disk, bulge, and central particles must use clearly different
   colours when their individual masses differ.
6. In `Liees / ejectees`, confirm ejected particles are red when any appear.
7. Enable the centre-of-mass marker and confirm the bright green marker appears
   near the physical centre.
8. Open `Statistiques`, then click directly on `Performances` and `Technique`.
   Each drawer must switch in one click, fit without scrolling, and close with a
   second click or `x`.
9. Confirm all displayed physical values remain finite.

The energy is intentionally labelled `estimee`. The ejection count is an
observational classification; particles are not removed from the solver.

## Galaxy masses

1. In the immobile preview, open `Masses avancees`.
2. Change the total disk, bulge, and central masses, then apply them.
3. Confirm the preview is regenerated without starting time evolution.
4. Select `Masse` and confirm the three particle-mass levels remain visible.
5. In a collision, confirm the displayed totals are split across the two
   galaxies rather than duplicated.

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
