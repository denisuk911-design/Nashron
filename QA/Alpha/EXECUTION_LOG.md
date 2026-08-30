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


