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

## Capture limitation

The connected Playwright Chrome timed out during its font-wait screenshot phase. No new screenshot is represented as evidence; existing baseline captures were not modified.

Post-capture review found that Settings was being rebuilt by the runtime controller after the initial shell render. The dynamic Settings content was corrected and the packaged build was rebuilt; a second DOM verification confirmed the corrected user-facing copy and viewport bounds.
