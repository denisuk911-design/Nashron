# Luminifera Runtime Migration Baseline

Date: 2026-08-30

BASE_COMMIT: `f875922` (`Freeze Luminifera Web working baseline`)
PYTHON_VERSION: `Python 3.14.5` (`.venv`)
WEB_STATUS: `http://127.0.0.1:3000/` returned `200`; Luminifera landing/workspace baseline is running
API_STATUS: `http://127.0.0.1:8000/api/health` returned `200`; product `Luminifera`, engine `Python Core / Runtime V3`
FULL_TEST_STATUS: `511 passed`, 2 non-fatal warnings
TARGETED_WEB_STATUS: `22 passed`, 2 non-fatal fixture/dependency warnings
NATIVE_RUNTIME_STATUS: Preserved and used by the existing Runtime V3 service-backed smoke; fresh smoke passed with 3 WorkItems, physical artifacts, evidence, Work Receipt and restart persistence
DB_SCHEMA_STATUS: No migration performed; existing SQLite schema and `PRAGMA foreign_key_check` baseline preserved
KNOWN_GAPS: Runtime is still selected through Native Runtime paths; runtime-neutral contracts, external candidate environments, adapters, selector and bake-off are not yet implemented

Untracked files shown by `git status` at baseline were preserved and are not part of this migration checkpoint:

- `QA/LuminiferaRebuild/EngineParity/runtime_v3_packaged_gui_smoke.json`
- `QA/LuminiferaRebuild/EngineParity/runtime_v3_packaged_gui_smoke.png`
- `QA/Web/LUMINIFERA_REVIEW_PACKAGE.zip`
- `QA/Web/SCREENSHOTS/landing-current.png`
