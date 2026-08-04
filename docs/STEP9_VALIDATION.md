# Step 9 Windows validation

This short check validates the parts that automated headless tests cannot prove:
font rendering, colour readability, fullscreen behaviour, and the visual feel of
the canonical camera views.

## Start

1. Run `INSTALLER.bat`, then `LANCER_GRAVITY.bat`.
2. Confirm the panel says `Jalon 9 · observer la physique`.
3. Confirm technical sections are folded and no text is cut at the right edge.

## Observation

1. Pause with `Space` and cycle through all five colour modes.
2. Confirm distance, speed, component, and energy produce visibly different maps.
3. In `Liees / ejectees`, confirm ejected particles are red when any appear.
4. Enable the centre-of-mass marker and confirm the bright green marker appears
   near the physical centre.
5. Open physical statistics and confirm all values remain finite.

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

## Compute ceiling

1. Launch 50'000 particles and raise requested speed to 2.5x.
2. Confirm the panel distinguishes requested and effective speed.
3. The renderer should remain responsive even when effective speed is below the
   request.
