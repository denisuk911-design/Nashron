# Phase 6 Product Function Depth

## Scope

The V3 product shell was updated without changing Core, API contracts, runtime selection, persistence, or provider behavior.

## Changes

- Work now renders real review findings from `/api/work/review` and exposes rework through the existing goal `replan` service.
- Theme, interface language, and reduced-motion settings are applied immediately after the real `/api/settings` save response.
- Team lifecycle controls continue to use the real employee role/archive/delete services and report Core errors in the product status strip.
- Home, workspace creation, Iris chat, goal actions, artifact preview/download, health check, and feedback remain connected to the existing bridge/API methods.
- Added focused regression checks for review/rework projection and persisted settings application.

## Verification

- `pytest -q tests/test_alpha_product_ui.py tests/test_luminifera_work_service.py`: PASS, 16 passed.
- `node --check apps/web/static/v3/app.js`: PASS.
- `node --check apps/web/static/v3/bridge.js`: PASS.
- `git diff --check`: PASS.
- Packaged build: `scripts/build_luminifera_web.bat`, PASS; `dist/Luminifera.exe` launched successfully in a bounded smoke check.
- `scripts/package_luminifera_runtime.py`: PASS; OpenAI Agents sidecar manifest regenerated.
- Full pytest: started, but the repository currently contains/had multiple long-running pytest processes and the run did not produce a completed result before the bounded execution window. No full-suite PASS is claimed.
- `scripts/packaged_preview_smoke.py` is for the legacy Team2050 preview executable and did not produce evidence for `dist/Luminifera.exe`; no legacy smoke PASS is claimed for this V3 package.

## Status

Targeted functional checks PASS. Full-suite and packaged end-to-end evidence remain open due the existing long-running test/smoke processes and the legacy smoke script targeting another executable.
