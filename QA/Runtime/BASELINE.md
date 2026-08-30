# Luminifera Runtime Migration Baseline

Date: 2026-08-30

BASE_COMMIT: `f875922` (`Freeze Luminifera Web working baseline`); current checkpoint `3abd5b8`
PYTHON_VERSION: `Python 3.14.5` (`.venv`)
WEB_STATUS: `http://127.0.0.1:3000/` returned `200`; Luminifera landing/workspace baseline is running
API_STATUS: `http://127.0.0.1:8000/api/health` returned `200`; product `Luminifera`, engine `Python Core / Runtime V3`
FULL_TEST_STATUS: baseline `511 passed`; current post-Alpha regression `547 passed`, 2 non-fatal warnings
TARGETED_WEB_STATUS: baseline `22 passed`; current Alpha/API targeted `23 passed`
NATIVE_RUNTIME_STATUS: Preserved and used by the existing Runtime V3 service-backed smoke; fresh smoke passed with 3 WorkItems, physical artifacts, evidence, Work Receipt and restart persistence
DB_SCHEMA_STATUS: No migration performed; existing SQLite schema and `PRAGMA foreign_key_check` baseline preserved
KNOWN_GAPS: external provider-backed normalized parity for quota-blocked candidates remains blocked; Native remains the production baseline

Untracked files shown by `git status` at baseline were preserved and are not part of this migration checkpoint:

- `QA/LuminiferaRebuild/EngineParity/runtime_v3_packaged_gui_smoke.json`
- `QA/LuminiferaRebuild/EngineParity/runtime_v3_packaged_gui_smoke.png`
- `QA/Web/LUMINIFERA_REVIEW_PACKAGE.zip`
- `QA/Web/SCREENSHOTS/landing-current.png`
