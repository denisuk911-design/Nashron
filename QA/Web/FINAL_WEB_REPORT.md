# Luminifera Web Report

WEB_STACK: FastAPI + vanilla ES modules-compatible browser UI (React/Next migration remains optional); uvicorn local server
FRONTEND_PATH: `apps/web/static`
API_PATH: `services/api/app.py`
RUN_COMMAND: `powershell -ExecutionPolicy Bypass -File .\scripts\run_web.ps1`
LANDING_STATUS: Implemented using supplied Iris poster and animation assets; responsive commercial art direction
APP_STATUS: Implemented local Product shell with organization, chat, team, work, files and connections/knowledge views; separate local Web (`3000`) and engine (`8000`) hosts
IRIS_REAL_CORE: Connected to `SupervisorChatApplicationService`; owner chat is persisted and responses are persisted
TEAM_REAL_CORE: Real organization-scoped employee read model
GOAL_REAL_CORE: Real Director service create/approve/replan/cancel routes with scope checks
ARTIFACT_REAL_CORE: Real artifact and file read models, server-side text preview and safe download endpoints
REVIEW_REAL_CORE: Existing Runtime V3/review engine preserved; Work Receipt API projects actual completion/evidence/findings/review state
REALTIME: WebSocket `/api/events` publishes organization, Iris and goal lifecycle events
ORG_ISOLATION: Server validates organization IDs and scopes product reads; auth/membership enforcement is the next deployment layer
LOCALIZATION: Initial product copy is Russian; settings API accepts RU/UA/EN and persists the selected language; provider, skill, memory and competence labels are human-facing
EXISTING_ENGINE_TESTS: `python -m pytest` completed with 498 passed in 157.48 seconds after Web service extraction
WEB_TESTS: targeted Web/API, management and supervisor-chat coverage: 28 passed; isolated service-backed smoke passed
SERVICE_SMOKE: `scripts/web_smoke.py` proves team creation, persisted Iris chat, Director plan creation and WebCore restart persistence in a clean profile
KNOWN_GAPS: Full WorkItem execution streaming, review/rework API, provider authentication flow and complete RU/UA/EN catalogs still need extraction and coverage; Phase 15 has an actual browser screenshot but final visual acceptance remains manual
LEGACY_PYSIDE_STATUS: Preserved unchanged as legacy fallback/test harness
COMMERCIAL_READINESS: Landing and local API foundation are present; auth, billing, quotas and cloud deployment are intentionally not implemented

This report does not claim final visual or commercial parity. It records the first usable Web foundation and the remaining service extraction work.
