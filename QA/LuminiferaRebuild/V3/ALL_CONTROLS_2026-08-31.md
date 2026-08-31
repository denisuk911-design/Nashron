# V3 all-controls gate - 2026-08-31

## Packaged E2E

- Binary: `dist/Luminifera.exe`
- Packaged URL: `http://127.0.0.1:59211/app`
- Hero Iris action focused the inline Iris composer.
- Prompt action populated the composer with its real prompt.
- Owner profile action opened Settings.
- Workspace dialog opened and the close control closed it.
- Home, Team, Work, Files and Settings navigation each activated the expected product screen.
- Global vertical scroll was absent and no raw internal IDs were shown.

## Fix

The organization dialog close control was intercepted by the form submit handler. The V3 controller now cancels that submit and explicitly closes the dialog. No visual redesign or fake data was added.

## Result

Packaged controls PASS. Targeted UI tests: 11 passed. Full pytest: 557 passed, 2 warnings.
