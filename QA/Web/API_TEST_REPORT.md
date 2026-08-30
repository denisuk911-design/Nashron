# Web API Test Report

- `.venv\Scripts\python.exe -m pytest -q tests/test_web_api.py`: **17 passed**.
- Uvicorn started on `127.0.0.1:8000`.
- `/`, `/api/docs`, and `/assets/iris_poster.png` returned HTTP 200.
- `/api/health` returned `status=ready`, product `Luminifera`, engine `Python Core / Runtime V3`.
- WebSocket organization isolation is covered by a two-client regression test; scoped events are delivered only to the subscribed organization.
- Browser verification on `http://127.0.0.1:3000/`: Luminifera landing renders the product sections, workspace is present, API status is connected, and Iris poster loads at its natural `1123x1400` resolution.

The full browser regression suite remains a hardening item after the remaining lifecycle routes are extracted. Existing Python engine tests remain the compatibility gate.

## 2026-08-29 - service-backed smoke expansion

- `python scripts/web_smoke.py --profile .tmp_web_smoke_20260829b --report QA/Web/web_smoke.json`: passed.
  - Professional team: created through `UniversalPlatformService`.
  - Iris chat: persisted through `SupervisorChatApplicationService` with `chat_result=true`.
  - Goal: created through `SupervisorApplicationService` / Director plan.
  - Restart: the organization remained visible from a newly created `WebCore`.
- `pytest tests/test_web_api.py tests/test_management_foundations.py tests/test_supervisor_chat_application_service.py`: **28 passed**.
- `git diff --check`: passed.

## Local Web stack probe

- `services.web_dev_server` at `127.0.0.1:13000`: `/` and `/assets/app.js` returned HTTP 200.
- FastAPI at `127.0.0.1:18000`: `/api/health` returned HTTP 200.
- The two hosts were shut down immediately after the probe.

## Team reassignment service

- `pytest tests/test_universal_platform_u1.py tests/test_web_api.py tests/test_management_foundations.py`: **20 passed**.
- The new unit check proves membership role reassignment is persisted through `UniversalPlatformService`; the Web endpoint also updates the employee profile through `ManagementService` before publishing its event.

## Full Python engine compatibility gate

- `python -m pytest`: **498 passed** in 157.48 seconds.
- Warnings: Starlette `TestClient` deprecation notice and an existing backup-fixture duplicate zip entry warning. No test failures.
