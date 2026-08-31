# Phase 7 Iris Presence Rebuild

## Scope

UI-only change for the packaged V3 Home scene. Core, API, runtime, persistence,
and data contracts were not changed.

## Implemented

- Removed the hard inner media frame, border, and decorative ring around Iris.
- Kept the supplied Iris image fully responsive with `contain` sizing so the
  portrait is not cropped or letterboxed.
- Blended and softly masked the supplied media edges into the Iris chamber so
  the portrait reads as a living presence rather than a framed avatar.
- Kept the inline Iris chat in the same chamber and retained the restrained
  ambient presence animation.

## Evidence

- Packaged runner: `scripts/luminifera_phase7_visual_e2e.py`
- Captures: `QA/PHASE7_LUMINIFERA_VISUAL/`
- Home captures: `home-1920x1080.png`, `home-1440x900.png`
- Additional route captures: Team, Work, Files, and Settings at both viewports.

## Verification

- Packaged `dist/Luminifera.exe`: PASS.
- 1920x1080 and 1440x900: PASS.
- Home/Team/Work/Files/Settings capture generation: PASS.
- Wheel navigation, theme application, and edge spring checks: PASS.
- Inline Iris chamber present: PASS.
- JS syntax (`app.js`, `v37-ui.js`): PASS.
- `git diff --check`: PASS.
- Targeted UI tests: PASS.
- Full pytest: `564 passed, 2 warnings`.

Final visual approval remains with the owner/reviewer.
