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
