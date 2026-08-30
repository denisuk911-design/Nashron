# Luminifera Web Working Baseline

Date: 2026-08-30
Branch: `main`
Functional baseline parent: `8bca03d`
Checkpoint commit: recorded by the commit that adds this file and the execution-log entry.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_web.ps1
```

- Web: `http://127.0.0.1:3000/`
- API/OpenAPI: `http://127.0.0.1:8000/api/docs`
- Health: `http://127.0.0.1:8000/api/health`

## Verified

- Full repository regression: `511 passed`, two non-fatal warnings.
- Targeted Web/API, scoped realtime, Skills and Knowledge lifecycle tests are green.
- Fresh isolated Web smoke: real team, Iris chat, Goal start, WorkItems, physical artifacts, evidence, Work Receipt and restart persistence.
- Landing screenshot: `QA/Web/SCREENSHOTS/landing-current-fixed.png`.
- PySide desktop UI remains preserved as legacy fallback/test harness.

## Scope boundary

This file freezes the current Web state as a working baseline. Further Web commercial, visual polish, provider UI, localization and runtime-decoupling work requires a new explicit task.

Known gaps remain documented in `QA/Web/FINAL_WEB_REPORT.md`; this baseline is not a claim of final commercial acceptance.
