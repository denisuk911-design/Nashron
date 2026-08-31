# PHASE 3 Functional Restore

Date: 2026-08-31

## Scope

The V3 Product UI was kept visually unchanged. Existing bridge/API routes are
used for Goal lifecycle actions, Work state, Settings health checks, and file
previews.

## Changes

- Added bridge calls for Goal approve, replan, cancel, health, and file preview.
- Work now loads real goals, work items, review findings, timeline, and receipt.
- Goal rows expose lifecycle actions backed by `/api/goals/{plan_id}` services.
- File preview uses the bridge so the organization header is preserved; content
  is shown in the existing product dialog instead of an unscoped new tab.
- Settings connection check now calls `/api/health` and reports the real result.

## Verification

- Packaged build: `dist/Luminifera.exe` rebuilt successfully.
- Packaged captures at 1920x1080: `QA/PHASE3_FUNCTIONAL_RESTORE_1920/manifest.json`.
- Packaged captures at 1440x900: `QA/PHASE3_FUNCTIONAL_RESTORE_1440/manifest.json`.
- Packaged route/bridge smoke: Home, Team, Work, Files, Settings active; health
  check, Work state shape, and file-preview control verified.
- Targeted pytest: `100 passed, 457 deselected`.
- Full pytest: `557 passed, 2 warnings`.
- JavaScript syntax: `node --check` for `app.js` and `bridge.js` passed.
- `git diff --check`: passed.

## Runtime note

The isolated `scripts/web_smoke.py` run created a real organization and team,
persisted Iris chat, created a Goal, produced 3 WorkItems, 1 artifact and 2
evidence records, and confirmed WebCore restart persistence. The runtime result
was `ok=false` because its final evidence policy rejected an unconfirmed claim;
this is reported as a runtime limitation, not marked as a false UI PASS.
