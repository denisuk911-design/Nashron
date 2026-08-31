# V3.5 Visual Refinement

## Scope

- Compact header Iris action and presence label.
- Improved Iris portrait/video framing while keeping inline chat on Home.
- User-facing Settings copy without provider/runtime plumbing.
- Select controls styled to match the product shell.
- Real Team members rendered as animated constellation nodes.

## Verification

- Packaged binary: `dist/Luminifera.exe`.
- Packaged URL: `http://127.0.0.1:63174/app`.
- 1920x1080: Home, Team, Work, Files and Settings opened; Iris media loaded; document/body scroll absent.
- 1440x900: Home, Team and Settings opened; 3 real Team nodes rendered; document/body scroll absent; native default select appearance disabled; technical Settings copy absent.
- Targeted UI tests: 11 passed.
- Full regression: 557 passed, 2 warnings.
- JavaScript syntax: `node --check apps/web/static/v3/app.js` passed.

## Screenshot runner fix and final evidence

The capture runner now uses Playwright's bundled Chromium by default. System Chrome was rejected by the machine's DevTools policy and caused false screenshot failures; `LUMINIFERA_CHROME_PATH` remains available as an explicit override.

Final packaged captures completed with `unavailable=[]`:

- `captures/v35-1920-final/manifest.json` and its Home/Team/Work/Files/Settings PNGs.
- `captures/v35-1440-final/manifest.json` and its Home/Team/Work/Files/Settings PNGs.

Post-capture review found that Settings was being rebuilt by the runtime controller after the initial shell render. The dynamic Settings content and the header workspace-select contrast were corrected, the package was rebuilt, and the final captures confirm readable user-facing copy and controls.
