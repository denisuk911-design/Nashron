# Web API Test Report

- `pytest tests/test_web_api.py`: **2 passed**.
- Uvicorn started on `127.0.0.1:8000`.
- `/`, `/api/docs`, and `/assets/iris_poster.png` returned HTTP 200.
- `/api/health` returned `status=ready`, product `Luminifera`, engine `Python Core / Runtime V3`.

The full browser regression suite remains a hardening item after the remaining lifecycle routes are extracted. Existing Python engine tests remain the compatibility gate.

## 2026-08-29 - service-backed smoke expansion

- `python scripts/web_smoke.py --profile .tmp_web_smoke_20260829b --report QA/Web/web_smoke.json`: passed.
  - Professional team: created through `UniversalPlatformService`.
  - Iris chat: persisted through `SupervisorChatApplicationService` with `chat_result=true`.
  - Goal: created through `SupervisorApplicationService` / Director plan.
  - Restart: the organization remained visible from a newly created `WebCore`.
- `pytest tests/test_web_api.py tests/test_management_foundations.py tests/test_supervisor_chat_application_service.py`: **28 passed**.
- `git diff --check`: passed.
