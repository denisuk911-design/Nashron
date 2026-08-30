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
- Final local smoke rerun on 2026-08-30: `checks_passed=true`; four-member team, persisted Iris chat, real Director goal creation and WebCore restart persistence all passed.

## Local Web launch checkpoint - 2026-08-30

- Standard stack is running from `scripts/run_web.ps1`: Web `http://127.0.0.1:3000`, API `http://127.0.0.1:8000`.
- Live probes returned HTTP 200 for `/`, `/runtime-config.js`, `/assets/iris_poster.png` and `/api/health`.
- Browser landing verification: title `Luminifera | AI workforce`, API state `API подключён`, Iris portrait loaded.
- Actual landing capture: `QA/Web/SCREENSHOTS/phase21_landing_actual.png`.

## Phase 12 product-safe goal detail checkpoint - 2026-08-30

- Added organization-scoped `GET /api/goals/{plan_id}` and switched goal list/create/update responses to a human-facing projection.
- Runtime assignment identifiers (`agent_id`, `task_id`, `run_id`) are excluded from the Product API; employee, role, step status, attempt, review and result remain available for the Work view.
- Targeted API suite: `11 passed`; API compilation and `git diff --check`: passed.
- Live standard-stack probe after restart: Web `200`, API health `200`, OpenAPI includes `/api/goals/{plan_id}`.

## Phase 14 artifact delivery checkpoint - 2026-08-30

- Product artifact view now carries durable artifact identity, source goal, creator and review status.
- Added scoped `/api/files/{file_id}/preview` and `/api/files/{file_id}/download` routes for both database artifacts and Runtime V3 checkpoint artifacts.
- Runtime file resolution is constrained to the organization runtime workspace; unknown and cross-scope files return `404`.
- Targeted API suite: `12 passed`; compilation and `git diff --check`: passed.
- Live API after restart: health `200`; OpenAPI contains both artifact delivery routes.
- Browser verification: Files view opens through the real client and correctly shows its empty state when the selected organization has no artifacts; no JavaScript errors observed.

## Phase 14 Web delivery controls - 2026-08-30

- Added real Open/Download controls for server-backed artifacts in the Files view. Text preview is rendered in a modal; binary files remain downloadable without pretending to preview them.
- Controls use organization-scoped artifact IDs and the new API delivery routes; no client-side file content or fake result is introduced.
- `node --check apps/web/static/actions.js`: passed.
- Isolated Web smoke after delivery changes: `checks_passed=true`; team size `4`, Iris chat `true`, real goal plan created, persistence after WebCore restart `true`. Evidence: `QA/Web/web_smoke_phase14.json`.

## Intermediate reviewer entry point - 2026-08-30

- Added `QA/Web/REVIEW_PACKAGE/README.md` with the review workflow and the current visual evidence path.
- Added `scripts/run_luminifera_review.ps1`, a wrapper that starts the same real Web/API stack and supports alternate ports for an isolated review.
- Review launcher probe on Web `3011` / API `8011`: both returned HTTP `200`; the temporary stack was stopped after verification.

## Phase 21 real Web goal execution checkpoint - 2026-08-30

- Extended `scripts/web_smoke.py` to start the created goal through the FastAPI route.
- Isolated run passed: `3` work items, `2` physical artifacts, `4` evidence records, a ready Work Receipt and restart persistence; `checks_passed=true`.
- Evidence: `QA/Web/web_smoke_phase21.json`.
- This proves the real Core/Runtime V3 path through Web API; it does not claim per-step WebSocket streaming or a separate review/rework command API.

## Phase 04 runtime event projection - 2026-08-30

- Goal start now derives WebSocket `work.*`, `artifact.created` and `review.*` events from persisted Runtime V3 trace records before publishing the final goal state.
- Event payloads include the organization scope and durable trace references; no animation-only event is generated.
- API suite remains green at `12 passed`; per-step delivery is intentionally still documented as a burst after synchronous runtime completion, not claimed as live streaming.
- Event projection smoke evidence: `QA/Web/web_smoke_events.json` also passed the real goal execution and receipt checks.

## Phase 04 checkpoint-streamed goal execution - 2026-08-30

- Runtime V3 execution now runs off the FastAPI event loop while the API watches the durable checkpoint and forwards new trace records to WebSocket subscribers.
- Trace-derived work, artifact and review events are emitted from actual Core state; the final response still contains the durable receipt.
- Isolated smoke after the change: `checks_passed=true`; 3 work items, 2 artifacts, 4 evidence records and restart persistence. Evidence: `QA/Web/web_smoke_streaming.json`.
- API suite: `12 passed`; compile and `git diff --check`: passed.

## Phase 19 reconnectable Work timeline - 2026-08-30

- Added `GET /api/work/timeline`, a scoped human-facing replay of Runtime V3 checkpoint traces.
- The Work view renders the latest persisted execution steps and marks saved artifacts, so a reload does not erase the visible history.
- API suite: `13 passed`; JavaScript syntax, compilation and `git diff --check`: passed. Browser verified the Work view and empty-state behavior with no errors.
