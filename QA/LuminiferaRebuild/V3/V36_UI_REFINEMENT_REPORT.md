# V3.6 UI Refinement Evidence

## Scope

Product UI only. Backend, API contracts, Application Services, runtime, persistence, providers, and real data sources were not changed.

Implemented:

- Iris portrait, presence, and inline chat are presented as one chamber.
- Workspace labels hide internal `ADVISORY_BOARD` naming.
- Team constellation uses real API employee nodes with larger nodes, links, and restrained animated light pulses.
- Work empty state shows a neutral `Goal -> Work -> Artifacts -> Review` flow without invented work.
- Settings uses the full viewport with a responsive three-column product layout.

## Evidence

- 1920x1080 captures: `QA/LuminiferaRebuild/V3/captures/v36-1920-final/`
- 1440x900 captures: `QA/LuminiferaRebuild/V3/captures/v36-1440-final/`
- Both manifests report no unavailable screens.

## Verification

- Targeted UI/API/work tests: 34 passed.
- Full pytest: 557 passed, 2 existing warnings.
- JavaScript syntax: `v36-ui.js` and `app.js` passed `node --check`.
- `git diff --check`: passed.
- Packaged build: `dist/Luminifera.exe` built successfully.
- Packaged launch smoke: process stayed alive after startup and was stopped cleanly.

Final pixel-level visual approval remains with the human reviewer.
