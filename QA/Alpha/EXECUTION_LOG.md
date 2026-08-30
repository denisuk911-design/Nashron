# Alpha Execution Log

## 2026-08-30 вЂ” Alpha Productization P0

- Replaced the Web landing/admin surface with a Product Mode workspace.
- Added navigation for Home, Iris, Team, Work, Files and Settings.
- Consolidated Iris portrait, presence, chat history and composer into one component; Home includes a compact Iris entry point.
- Removed the legacy Web controller from the page load so old technical/debug UI cannot run alongside the product shell.
- Added health-gated Web/API launcher and Windows batch entry point.
- Added targeted UI contract tests and Alpha QA reports.
- Browser check completed against the launcher on ports 3011/8011.

## 2026-08-30 — Closed Alpha P0 delivery checkpoint

- Added separate landing (/) and Product App (/app); launcher now opens /app.
- Added secure provider connect/check/disconnect endpoints; credentials remain in the existing OS credential boundary and READY is based on real health.
- Added organization-scoped persistent Feedback Inbox and safe diagnostics endpoint; feedback does not create a Goal.
- Added Settings UI for AI connections, feedback and diagnostics without exposing secrets or runtime internals.
- Added landing/app route contract tests and verified actual /app HTTP response plus browser screenshot.
- Full regression: 548 passed, 2 existing warnings. Packaged Team2050.exe build and packaged preview smoke passed.
- Remaining Alpha review item: full packaged Web E2E and complete review screenshot set require a Web-enabled distribution path; current PySide package build does not embed the Web launcher.

## 2026-08-30 — Web Alpha package checkpoint

- Added `LuminiferaWeb.spec` and `scripts/luminifera_web_launcher.py`: one-file executable starts API and Web, waits for health, opens `/app`, and shuts down both services together.
- Built `dist/Luminifera.exe`; direct packaged smoke reached `/app`, loaded all Product assets and returned HTTP 200.
- Added `QA/Alpha/Luminifera-Web-Alpha.zip` and `WEB_ALPHA_QUICK_START.md`.

## 2026-08-30 - Packaged E2E and startup stabilization

- Fixed packaged windowed startup by providing silent writable standard streams for Uvicorn logging.
- New team creation now assigns the first genuinely READY provider as a wildcard fallback; unconfigured teams remain honest and report missing providers.
- Packaged `dist/Luminifera.exe` fresh-profile E2E: readiness, organization, team, Goal, restart and shutdown PASS.
- Goal result: 3 WorkItems, 2 verified artifacts, 4 evidence records, review PASS, 0 findings, durable receipt.
- Targeted tests: 29 passed. Full pytest: 549 passed, 2 warnings.
- Final packaged readiness check: `/app` opened, API health PASS, controlled stop PASS.
- Packaged browser capture produced six populated product views plus landing and live provider/profile views. `LUMINIFERA_VISUAL_REVIEW.zip` contains exactly eight captures, the E2E report, source snapshot and known limitations for human review.

## 2026-08-30 - Isolated visual capture gate

- Added `scripts/capture_visual_gate.py`, a standalone Python Playwright runner using local Chromium and an isolated profile; it does not use the browser extension or mutate product data.
- Ran it against packaged `dist/Luminifera.exe`: all six product views, landing, Settings and the real Feedback section captured; manifest reported `unavailable=[]`.
- Created `LUMINIFERA_VISUAL_REVIEW_STANDALONE.zip` with captures, manifest, runner and current evidence. BYOK/Feedback remain documented as Settings sections because the product has no separate routes for them.

## 2026-08-30 - Visual Rework Round 1

- Added `apps/web/static/premium.css` as the shared Product UI layer for Home, Iris, Team, Work, Files and Settings/BYOK/Feedback.
- Rebalanced the workspace around a persistent sidebar, clearer typography and spacing, compact status rail, unified controls and Iris as the visual center.
- Rebuilt packaged captures through the hardened standalone runner: landing, Home, Iris, Team, Work, Files, Settings, BYOK and Feedback all captured with `unavailable=[]`.
- Targeted regression: 25 passed. Full pytest: 549 passed, 2 existing warnings.
- Rebuilt `dist/Luminifera.exe` and verified the packaged `/app` screen plus real API-backed Product views.
- Refreshed `QA/Alpha/LUMINIFERA_VISUAL_REVIEW_STANDALONE.zip` and manifest.
- Status: `READY_FOR_HUMAN_VISUAL_REVIEW`; Final Alpha PASS intentionally not declared.

## 2026-08-30 - Visual Rework Round 2

- Rebuilt client composition in `apps/web/static/premium-rework.js`: Home is organized around current focus and Iris, Iris is a dedicated work center, Team is a role/status workspace, Work is a Goal-to-execution flow, and Files is a results library.
- Removed duplicate visible top navigation while preserving the existing sidebar navigation and all API-backed actions.
- Added matching structural styles for focus, flow, team members, artifact library and Iris chat composition.
- Hardened `scripts/capture_visual_gate.py` to select the visible sidebar navigation after the duplicate top-nav control was removed.
- Packaged capture completed with `unavailable=[]`; Iris and Home visual inspection passed.
- Targeted regression: 25 passed. Fresh full pytest: 549 passed, 2 existing warnings.
- Round 2 evidence is ready for human visual review; Final Alpha PASS intentionally not declared.


