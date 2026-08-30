# Luminifera Web Execution Log

## 2026-08-29 - Web-first checkpoint and foundation

- Preserved the validated Python Core, Runtime V3, Application Services and PySide client.
- Added the Phase 01 readiness audit.
- Added the Phase 02 structure: `apps/web`, `services/api`.
- Added a FastAPI boundary with OpenAPI, organization-scoped read models, Iris chat, goals, work, files, artifacts, providers, settings and WebSocket events.
- Added a browser Product UI foundation using the supplied Iris poster asset and the Web prototype art direction.
- No fake backend action is used by the web UI: visible organization/chat data comes from API calls and SQLite-backed services.

## Verification

- `pytest tests/test_web_api.py tests/runtime_v3 tests/test_supervisor_chat_application_service.py`: 54 passed.
- `python -m compileall -q services/api`: passed.
- `git diff --check`: passed.
- Live uvicorn smoke: `/`, `/openapi.json`, `/api/health`, `/assets/iris_poster.png` returned 200.
- Browser screenshot acceptance is not claimed because this environment has no browser automation runtime.

## Runtime V3 web handoff

- Added `POST /api/goals/{plan_id}/start`.
- It runs the existing `RuntimeV3GoalService` with the same Codex/Gemini adapter model and permission resolver as the desktop client.
- The endpoint reports actual artifact/evidence/findings counts and emits real lifecycle events; provider failure remains a failure and is never converted to a fake completed result.

## Team lifecycle API smoke

- Isolated profile smoke created `Web E2E` organization through HTTP, hired `Mira`, returned a scoped roster with HTTP 200, and rejected deletion without confirmation with HTTP 409.
- This verifies the web boundary uses `UniversalPlatformService` and `ManagementService`, including the destructive-action gate.

## Artifact delivery boundary

- Added authenticated-in-future, organization-scoped artifact `preview` and `download` endpoints.
- The API resolves artifact paths through `PathGuard` on the server; Product UI receives artifact identity and safe content only, never a raw workspace path.

## Product Work Receipt

- Added a durable `WorkReceiptView` read model and `/api/work/receipt`.
- It projects only human-facing completion, artifacts, evidence count, findings count and review status from Runtime V3 checkpoints.

## Human-facing provider, skill and knowledge surfaces

- Provider responses now use `ProviderRegistry` and persisted health rather than raw database rows; Product labels are Ready, Login required, Busy, Error or Unavailable.
- Skills and knowledge now serialize service-owned product view models instead of table-shaped internal records.

## Social chat attachments

- Added multipart upload with a 20 MiB bound and durable `ChatAttachmentService` storage.
- Attachment IDs are bound to the owner message only after the message exists; binary data is never inserted into chat text or sent to Iris as an untracked claim.

## Deterministic service-backed smoke

- Added `scripts/web_smoke.py` for a repeatable Web boundary check in an isolated `TEAM2050_HOME` profile.
- The smoke creates a professional team through `UniversalPlatformService`, persists an Iris chat message, creates a Director plan, and verifies the organization survives a new `WebCore` instance.
- A missing director now returns HTTP 409 `director_not_assigned` instead of leaking a 500 from the API boundary.
- Latest isolated run: `checks_passed=true`, four provisioned team members, Iris chat result `true`, durable plan created.

## Local Web development stack

- Added `services.web_dev_server` as a thin static host for the Product UI on port 3000.
- `scripts/run_web.ps1` now starts the static shell and FastAPI engine as separate local processes; browser API and WebSocket requests are directed to the engine on port 8000.
- Probe run on alternate ports returned HTTP 200 for the Web entrypoint, `app.js`, and API health. The temporary probe processes were stopped after verification.

## Team lifecycle controls

- The Team view now exposes real archive and delete controls for each scoped employee.
- Archive calls the existing ManagementService-backed endpoint. Delete requires a browser confirmation and the server-side `confirm=true` gate.
- Role reassignment is now extracted through `ManagementService` plus `UniversalPlatformService`, so profile roles and organization routing roles remain consistent.

## Full compatibility verification

- Full Python engine suite passed: `498 passed` in 157.48 seconds.
- Web service extraction has not broken the existing Runtime V2/V3, management, organization, chat or PySide compatibility coverage.

## Phase 15 - providers, skills and organization knowledge

- Added a dedicated `Подключения` product view backed by the provider registry, skill packages, organization memory and competence graph.
- Provider checks call the real provider-health endpoint; the UI never changes availability optimistically.
- Knowledge and competence reads are server-scoped by organization and contain only durable Core records. Competence growth is shown as evidence-backed points, not an invented percentage.
- Added runtime Web/API configuration so non-default local ports work without rebuilding frontend assets.
- Browser verification used the local Web host on port 3015 and API on port 8015. The view rendered successfully with no JavaScript console errors and no repeated request loop.
- Actual browser capture: `QA/Web/SCREENSHOTS/phase15_connections_actual.png`.
- Phase 15 targeted tests: `14 passed`; deterministic Web smoke: `checks_passed=true`; JavaScript syntax, Python compilation and `git diff --check`: passed.
- Restored the supplied canonical Iris poster and animation in the static bundle. Browser verification reported portrait width `1123` and video ready state `4`; direct asset probes returned HTTP 200.

## Phase 16 - owner profile and settings surface

- Added server-backed owner profile read/update endpoints and a validated avatar catalog. The Web profile dialog exposes manual owner name editing and avatar selection without mixing employee identities.
- Added persisted settings fields for owner display name, avatar, reduced motion and developer mode. Existing language, theme and sound settings remain service-backed.
- The settings surface now exposes language choices RU/UA/EN, theme, sound, animation, AI connection guidance, local data policy and developer mode.
- Browser verification on the local Web client: profile dialog opened, `97` avatar options loaded, settings sections rendered, and dark select controls reported readable colors (`#0a1025` / `#eef2ff`).
- Actual browser capture: `QA/Web/SCREENSHOTS/phase16_profile_actual.png`.
- Phase 16 API tests: `10 passed`; JavaScript syntax and Python compilation: passed.

## Phases 17-20 - security foundation, legacy policy and local run

- Confirmed organization scope is enforced in the FastAPI boundary before service reads/writes; invalid organization IDs return `404 organization_not_found`.
- Preserved Python Core, Runtime, Application Services and PySide as the legacy fallback/test harness. No desktop UI was removed.
- `WEB_RUNBOOK.md` documents prerequisites, install, run, API docs, tests, isolated smoke and troubleshooting. The static host accepts an explicit API base for non-default local ports while the default remains Web `3000` and API `8000`.
- Full engine regression suite after Phase 16: `501 passed`, 2 non-fatal dependency/fixture warnings.
- Packaged-style browser smoke found and fixed a modal-close regression that blocked navigation after opening settings. Recheck passed: settings closes, `Подключения` becomes active, the real provider view renders, and browser errors are empty.
