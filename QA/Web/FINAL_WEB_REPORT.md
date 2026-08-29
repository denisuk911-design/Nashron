# Luminifera Web Report

WEB_STACK: FastAPI + vanilla ES modules-compatible browser UI (React/Next migration remains optional); uvicorn local server
FRONTEND_PATH: `apps/web/static`
API_PATH: `services/api/app.py`
RUN_COMMAND: `.venv\Scripts\python.exe -m services.api.run`
LANDING_STATUS: Implemented using supplied Iris poster and animation assets; responsive commercial art direction
APP_STATUS: Implemented local Product shell with organization, chat, team, work and files views
IRIS_REAL_CORE: Connected to `SupervisorChatApplicationService`; owner chat is persisted and responses are persisted
TEAM_REAL_CORE: Real organization-scoped employee read model
GOAL_REAL_CORE: Real Director service create/approve/replan/cancel routes with scope checks
ARTIFACT_REAL_CORE: Real artifact and file read models, server-side text preview and safe download endpoints
REVIEW_REAL_CORE: Existing Runtime V3/review engine preserved; Work Receipt API projects actual completion/evidence/findings/review state
REALTIME: WebSocket `/api/events` publishes organization, Iris and goal lifecycle events
ORG_ISOLATION: Server validates organization IDs and scopes product reads; auth/membership enforcement is the next deployment layer
LOCALIZATION: Initial product copy is Russian; settings API accepts RU/UA/EN and persists the selected language
EXISTING_ENGINE_TESTS: Not rerun in this web foundation checkpoint; no core files were changed
WEB_TESTS: `tests/test_web_api.py` passed (2 tests)
KNOWN_GAPS: Employee/team mutation forms, full WorkItem execution streaming, artifact download/preview, review/rework API, provider auth UI, complete RU/UA/EN catalogs and browser visual acceptance still need extraction and coverage
LEGACY_PYSIDE_STATUS: Preserved unchanged as legacy fallback/test harness
COMMERCIAL_READINESS: Landing and local API foundation are present; auth, billing, quotas and cloud deployment are intentionally not implemented

This report does not claim final visual or commercial parity. It records the first usable Web foundation and the remaining service extraction work.
