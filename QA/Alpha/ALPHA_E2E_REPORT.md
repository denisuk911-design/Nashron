# Alpha E2E Report

Checkpoint date: 2026-08-30

Browser verification was run against the packaged-style launcher on `http://127.0.0.1:3011` with API `http://127.0.0.1:8011`.

- First launch: PASS. API health gate completed before Web became available.
- Organization load and scoped Home: PASS.
- Iris component: PASS. Portrait, presence, saved context and composer rendered.
- Navigation: PASS for Home, Iris, Team, Work, Files and Settings.
- Product-mode surface: PASS. Provider/runtime/debug internals are absent from the navigation and controller.
- API requests observed: organizations 200, organization home 200, chat 200.

Goal execution, artifact opening and restart persistence remain covered by the existing Web API and runtime regression suites; the Alpha Web shell consumes those established service contracts.

Regression verification: `pytest -q` -> 547 passed, 2 known warnings. Packaged verification: `scripts/packaged_preview_smoke.py` -> `checks_passed: true` across first launch and restart.
