# V3.7 UI refinement evidence

## Scope

UI-only refinement after the V3.6 visual review. Core, API, runtime,
Application Services, persistence, and data contracts were not changed.

## Changes

- Team nodes now keep uniform contrast and readable avatars; activity remains
  expressed by the status glow and `ACTIVE` label.
- Settings uses a two-column layout with a full-width feedback area, removes
  the developer-facing media reload control, and presents system state as
  `Система подключена` / `Проверить систему`.
- Home summary cards and Iris chat framing are lighter and less dashboard-like.
- Work flow is placed inside the same centered empty-state composition instead
  of floating as a separate top strip.

## Captures

- `captures/v37-1920-final/home.png`
- `captures/v37-1920-final/team.png`
- `captures/v37-1920-final/work.png`
- `captures/v37-1920-final/settings.png`
- `captures/v37-1440-final/home.png`
- `captures/v37-1440-final/team.png`
- `captures/v37-1440-final/work.png`
- `captures/v37-1440-final/settings.png`
- Packaged copies: `captures/v37-packaged-1920/` and
  `captures/v37-packaged-1440/`

## Verification

- Targeted UI/API tests: `32 passed, 1 warning`.
- Full pytest: `557 passed, 2 warnings`.
- `node --check apps/web/static/v3/v36-ui.js`: PASS.
- `node --check apps/web/static/v3/app.js`: PASS.
- `git diff --check`: PASS.
- `scripts/build_luminifera_web.bat`: PASS, packaged `dist/Luminifera.exe`.
- Packaged capture runner: both viewports and all required routes captured;
  no unavailable screens; packaged process stopped via launcher stop file.

Final pixel-level visual approval remains with the reviewer.
