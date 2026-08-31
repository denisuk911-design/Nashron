# UI Audit And Blocker Fixes

Date: 2026-08-31

## Fixed

- Settings now maps the persisted `night_city` theme to the visible `Ночной город` option and sends the same backend value when saved.
- Iris chat suppresses adjacent duplicate messages with the same role and content, while preserving non-adjacent repeated messages.

## Verification

- Packaged `dist/Luminifera.exe` rebuilt successfully.
- Packaged captures completed with `unavailable=[]` at `1920x1080` and `1440x900`:
  - `QA/PHASE2_UI_AUDIT_0831/verified-1920/manifest.json`
  - `QA/PHASE2_UI_AUDIT_0831/verified-1440/manifest.json`
- Browser smoke against the packaged Web port confirmed:
  - theme value `night_city`, label `Ночной город`;
  - Iris media loaded;
  - `LuminiferaBridge.connected === true`;
  - no document or body vertical scroll;
  - no adjacent duplicate rendered messages.
- `node --check apps/web/static/v3/app.js`: PASS.
- `git diff --check`: PASS.
- Targeted pytest: `50 passed, 1 warning`.
- Full pytest: `557 passed, 2 warnings`.

The two warnings are existing dependency/fixture warnings and do not fail the suite.
