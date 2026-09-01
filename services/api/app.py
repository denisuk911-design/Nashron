from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
if os.environ.get("TEAM2050_PROJECT_ROOT"):
    ROOT = Path(os.environ["TEAM2050_PROJECT_ROOT"]).resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.agent_directory import list_chat_agents
from core.config_repository import ConfigurationRepository
from core.database import Database
from core.luminifera_files_service import LuminiferaFilesService
from core.luminifera_home_service import LuminiferaHomeService
from core.luminifera_work_service import LuminiferaWorkService
from core.management_service import ManagementService
from core.management_models import AgentProfile, OWNER_ROLE, ROLE_DEFAULT_PERMISSIONS
from core.path_guard import PathGuard, PathGuardError
from core.profile_backup_service import ProfileBackupError, ProfileBackupService
from core.codex_client import CodexClient
from core.gemini_client import GeminiClient
from core.provider_credentials import ProviderCredentialService
from core.provider_service import CodexProviderAdapter, GeminiProviderAdapter, ProviderHealthService, ProviderRegistry
from core.runtime_v3_service import RuntimeV3GoalService
from core.runtime_execution_service import RuntimeExecutionService
from core.external_runtime_factory import build_external_runtime_adapters
from core.runtime_journal import RuntimeExecutionJournal
from core.iris_orchestration_service import IrisExecutionContext, IrisOrchestrationService
from core.runtime_contracts import ExecutionPolicy
from core.settings_service import SettingsService
from core.supervisor_application_service import SupervisorApplicationService
from core.supervisor_chat_service import SupervisorChatApplicationService
from core.universal_platform_service import UniversalPlatformService
from core.tool_access import effective_permissions_for_agent
from core.skill_package_service import SkillPackageService
from core.knowledge_service import KnowledgeService
from core.chat_attachment_service import ChatAttachmentService
from core.competence_graph_service import CompetenceGraphService
from core.capability_registry import CapabilityRegistry
from core.capability_router import CapabilityRouter
from core.capability_service import CapabilityExecutionService
from core.avatar_catalog import list_avatar_files
from core.admin_center_service import AdminAccessError, AdminCenterService, PolicyDeniedError
from core.auth_service import AccountAuthService, AuthenticationError
from runtime_v3.models import load_state
from services.api.events import EventEnvelope


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    attachment_ids: list[str] = Field(default_factory=list, max_length=8)


class ProviderConnectionRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=20_000)


class FeedbackRequest(BaseModel):
    category: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=10_000)


class OrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    purpose: str = Field(default="", max_length=2_000)


class OrganizationUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    purpose: str = Field(default="", max_length=2_000)


class GoalRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=10_000)


class ExecutionApiRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=20_000)
    policy: ExecutionPolicy = ExecutionPolicy.CONVERSATIONAL
    preferred_runtime: str = Field(default="", max_length=80)


class SettingsRequest(BaseModel):
    interface_language: str | None = None
    theme: str | None = None
    onboarding_skipped: bool | None = None
    message_sounds_enabled: bool | None = None
    reduce_motion: bool | None = None
    developer_mode: bool | None = None
    owner_display_name: str | None = Field(default=None, max_length=120)
    user_avatar_path: str | None = Field(default=None, max_length=240)
    active_provider_id: str | None = Field(default=None, max_length=80)
    active_model_id: str | None = Field(default=None, max_length=160)


class ProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    avatar: str = Field(default="", max_length=240)


class EmployeeRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    role_id: str = Field(default="CUSTOM_ROLE", min_length=1, max_length=80)
    description: str = Field(default="", max_length=2_000)
    provider_id: str = Field(default="UNAVAILABLE", max_length=80)


class EmployeeRoleRequest(BaseModel):
    role_id: str = Field(min_length=1, max_length=80)


class SkillPackageRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    purpose: str = Field(default="", max_length=2_000)
    supported_roles: list[str] = Field(default_factory=list, max_length=20)
    instructions: str = Field(default="", max_length=10_000)
    tools: list[str] = Field(default_factory=list, max_length=40)
    version: str = Field(default="0.1.0", max_length=40)


class SkillStatusRequest(BaseModel):
    status: str = Field(min_length=1, max_length=40)
    reason: str = Field(default="", max_length=2_000)


class KnowledgeProposalRequest(BaseModel):
    source_run_id: str = Field(min_length=1, max_length=120)
    competence: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20_000)
    outcome: str = Field(default="PASS", max_length=20)


class KnowledgeVerifyRequest(BaseModel):
    review_run_id: str = Field(min_length=1, max_length=120)


class TeamRequest(BaseModel):
    brief: str = Field(min_length=3, max_length=5_000)
    organization_name: str = Field(min_length=1, max_length=160)
    template_id: str | None = None
    team_size: str = Field(default="STANDARD", max_length=30)


class AdminUserStatusRequest(BaseModel):
    status: str = Field(min_length=1, max_length=20)
    confirm: bool = False


class AdminConfirmationRequest(BaseModel):
    confirm: bool = False


class AuthLoginRequest(BaseModel):
    account_id: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=500)


class AuthRegisterRequest(BaseModel):
    account_id: str = Field(min_length=3, max_length=120)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=500)
    language: str = Field(default="ru", pattern="^(ru|uk|en)$")


class AuthBootstrapRequest(AuthRegisterRequest):
    pass


class AuthPasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=500)


class AdminCredentialRequest(BaseModel):
    password: str = Field(min_length=1, max_length=500)
    confirm: bool = False


class AdminProviderPolicyRequest(BaseModel):
    priority: int = Field(default=100, ge=0, le=10_000)
    fallback_provider_id: str | None = Field(default=None, max_length=80)
    max_requests: int | None = Field(default=None, ge=1, le=10_000_000)
    timeout_seconds: int = Field(default=180, ge=1, le=3600)
    retries: int = Field(default=1, ge=0, le=10)
    enabled: bool = True
    allowed_models: list[str] = Field(default_factory=list, max_length=100)
    default_model: str | None = Field(default=None, max_length=160)
    daily_request_limit: int | None = Field(default=None, ge=1)
    monthly_request_limit: int | None = Field(default=None, ge=1)
    daily_token_limit: int | None = Field(default=None, ge=1)
    monthly_token_limit: int | None = Field(default=None, ge=1)
    daily_cost_limit: float | None = Field(default=None, ge=0)
    monthly_cost_limit: float | None = Field(default=None, ge=0)


class AdminAccountRequest(BaseModel):
    role: str | None = Field(default=None, max_length=30)
    plan: str | None = Field(default=None, max_length=80)
    revoke_sessions: bool = False


class ProviderUsageRequest(BaseModel):
    account_id: str = Field(default="owner", min_length=1, max_length=120)
    provider_id: str = Field(min_length=1, max_length=80)
    organization_id: str | None = Field(default=None, max_length=120)
    model_id: str | None = Field(default=None, max_length=160)
    runtime: str | None = Field(default=None, max_length=80)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    fallback: bool = False
    cost: float | None = Field(default=None, ge=0)
    cost_status: str = Field(default="unavailable", max_length=30)


class PricingRequest(BaseModel):
    provider_id: str = Field(min_length=1, max_length=80)
    model_id: str = Field(min_length=1, max_length=160)
    input_price_per_million: float | None = Field(default=None, ge=0)
    output_price_per_million: float | None = Field(default=None, ge=0)
    effective_from: str = Field(min_length=10, max_length=40)
    currency: str = Field(default="USD", min_length=3, max_length=8)
    source_note: str = Field(default="", max_length=500)
    version: str = Field(default="1", max_length=40)


class AdminSettingsRequest(BaseModel):
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    registration_enabled: bool | None = None
    session_ttl_hours: int | None = Field(default=None, ge=1, le=8760)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=100_000)
    maintenance_mode: bool | None = None


class TelemetryRequest(BaseModel):
    event_type: str = Field(min_length=2, max_length=80)
    user_id: str = Field(default="owner", min_length=1, max_length=120)
    detail: dict[str, Any] = Field(default_factory=dict)


class ConnectionHub:
    def __init__(self) -> None:
        self._clients: dict[WebSocket, str | None] = {}

    async def add(self, socket: WebSocket, organization_id: str | None = None) -> None:
        await socket.accept()
        self._clients[socket] = organization_id

    def remove(self, socket: WebSocket) -> None:
        self._clients.pop(socket, None)

    async def publish(self, event: dict[str, Any]) -> None:
        envelope = EventEnvelope.model_validate(event) if "occurred_at" in event else EventEnvelope.create(event["type"], event["data"])
        payload = envelope.model_dump_json()
        stale: list[WebSocket] = []
        event_organization_id = event.get("data", {}).get("organization_id")
        for socket, organization_id in tuple(self._clients.items()):
            if event_organization_id and organization_id != event_organization_id:
                continue
            try:
                await socket.send_text(payload)
            except Exception:
                stale.append(socket)
        for socket in stale:
            self.remove(socket)


class WebCore:
    """Application boundary used by HTTP handlers; no product logic lives in the UI."""

    def __init__(self) -> None:
        self.settings_service = SettingsService(project_root=ROOT)
        self.paths = self.settings_service.ensure_user_files()
        self.settings = self.settings_service.load()
        self.database = Database(self.paths.database_path)
        self.database.initialize()
        self.management = ManagementService(
            self.database, ConfigurationRepository(self.paths.management_config_dir)
        )
        self.management.ensure_foundations()
        self.database.ensure_organization_conversations()
        self.workspace_root = Path(self.settings.get("workspace_root") or self.paths.workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.universal = UniversalPlatformService(
            self.database,
            management_service=self.management,
            workspace_root=self.workspace_root,
            identity_language=str(self.settings.get("interface_language", "ru")),
            avatar_dir=self.paths.avatar_dir,
        )
        self.universal.seed_management_library()
        self.provider_credentials = ProviderCredentialService(self.database)
        runtime_workspace = self.workspace_root / "web_provider_runtime"
        self.codex_client = CodexClient(
            workspace=runtime_workspace / "codex",
            timeout_seconds=int(self.settings.get("codex_timeout_seconds", 180)),
            logger=logging.getLogger("luminifera.web"),
        )
        self.gemini_client = GeminiClient(
            workspace=runtime_workspace / "gemini",
            timeout_seconds=int(self.settings.get("codex_timeout_seconds", 180)),
            credential_lookup=lambda: self.provider_credentials.read("GEMINI_CLI"),
            logger=logging.getLogger("luminifera.web"),
        )
        self.provider_adapters = {
            "CODEX_CLI": CodexProviderAdapter(self.codex_client),
            "GEMINI_CLI": GeminiProviderAdapter(self.gemini_client),
        }
        self.provider_registry = ProviderRegistry(self.database)
        self.provider_registry.ensure_defaults()
        self.provider_health = ProviderHealthService(self.database, self.provider_registry, self.provider_adapters)
        self.admin = AdminCenterService(
            self.database,
            settings=self.settings,
            management=self.management,
            providers=self.provider_registry,
            health=self.provider_health,
            credentials=self.provider_credentials,
        )
        self.auth = AccountAuthService(self.database)
        self.runtime_v3 = RuntimeV3GoalService(
            self.workspace_root / "runtime_v3_goals",
            provider_adapters=self.provider_adapters,
            permission_resolver=lambda agent_id: effective_permissions_for_agent(self.database, agent_id),
        )
        runtime_root = Path(os.environ.get("TEAM2050_RUNTIME_ROOT") or ROOT).resolve()
        active_provider = str(self.settings.get("active_provider_id") or "")
        selected_credential = self.provider_credentials.read(active_provider) if active_provider else None
        external_runtime_adapters = build_external_runtime_adapters(
            runtime_root,
            credential=(
                selected_credential
                or self.provider_credentials.read("OPENAI_API")
                or self.provider_credentials.read("GEMINI_CLI")
                or ""
            ),
        )
        self.runtime_execution = RuntimeExecutionService(
            self.runtime_v3,
            external_adapters=external_runtime_adapters,
            journal=RuntimeExecutionJournal(self.workspace_root / "runtime_execution"),
            promoted_runtime_ids={"openai-agents"} if "openai-agents" in external_runtime_adapters else set(),
            permission_resolver=lambda agent_id: effective_permissions_for_agent(self.database, agent_id),
            provider_settings=self.settings,
        )
        # Capability implementations are registered by dedicated tool services;
        # an empty registry honestly reports unavailable capabilities in Beta.
        self.capability_registry = CapabilityRegistry()
        self.capability_service = CapabilityExecutionService(
            CapabilityRouter(self.capability_registry),
            permission_resolver=lambda _organization_id, agent_id: (
                effective_permissions_for_agent(self.database, agent_id) if agent_id else ()
            ),
        )
        self.iris_orchestration = IrisOrchestrationService(
            self.runtime_execution, self.capability_service
        )
        self.supervisor = SupervisorApplicationService(self.database)
        self.chat = SupervisorChatApplicationService(
            supervisor_service=self.supervisor,
            universal_service=self.universal,
            management_service=self.management,
            settings=self.settings,
            save_settings=self._save_settings,
        )
        runtime_root = self.workspace_root / "runtime_v3_goals"
        self.home = LuminiferaHomeService(self.database, runtime_root)
        self.work = LuminiferaWorkService(self.database, runtime_root)
        self.files = LuminiferaFilesService(self.database, runtime_root)
        self.skills = SkillPackageService(self.database)
        self.knowledge = KnowledgeService(self.database)
        self.competence = CompetenceGraphService(self.database)
        self.attachments = ChatAttachmentService(self.database, self.workspace_root)
        self.backups = ProfileBackupService()
        self.events = ConnectionHub()

    def _save_settings(self, values: dict[str, Any]) -> None:
        self.settings_service.save(values)

    def organization_id(self, requested: str | None) -> str | None:
        if requested:
            allowed = {str(row["id"]) for row in self.database.list_organizations()}
            if requested not in allowed:
                raise HTTPException(status_code=404, detail="organization_not_found")
            return requested
        return self.database.get_active_organization_id()

    def conversation_id(self, organization_id: str | None) -> int:
        if organization_id:
            return self.database.ensure_organization_conversation(organization_id)
        return self.database.ensure_general_conversation()


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    return value


def _row(row: Any) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _public_plan(plan: Any) -> dict[str, Any]:
    """Expose a product-safe goal view without runtime or database internals."""
    payload = _plain(plan)
    payload.pop("director_agent_id", None)
    payload.pop("owner_message_id", None)
    public_assignments = []
    for assignment in payload.pop("assignments", []):
        public_assignments.append({
            "employee_name": assignment.get("employee_name", ""),
            "role": assignment.get("role_id", ""),
            "position": assignment.get("position", ""),
            "type": assignment.get("assignment_type", ""),
            "status": assignment.get("status", ""),
            "sequence": assignment.get("sequence_no", 0),
            "attempt": assignment.get("attempt_no", 0),
            "review": assignment.get("review_decision", ""),
            "summary": assignment.get("result_summary", ""),
            "failure": assignment.get("failure_reason", ""),
        })
    payload["assignments"] = public_assignments
    return payload


core = WebCore()
app = FastAPI(title="Luminifera API", version="0.1.0", docs_url="/api/docs", redoc_url="/api/redoc")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"^http://(?:localhost|127\.0\.0\.1)(?::\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Cache-Control", "no-store" if request.url.path.startswith("/api/auth") else "no-cache")
    return response


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ready", "product": "Luminifera", "engine": "Python Core / Runtime V3"}


@app.get("/api/build-info")
def build_info() -> dict[str, str]:
    """Expose deployment provenance without credentials or internal identifiers."""
    return {
        "product": "Luminifera",
        "commit": os.environ.get("RENDER_GIT_COMMIT", os.environ.get("GIT_COMMIT", "unknown")),
        "build_time": os.environ.get("RENDER_GIT_COMMIT_TIMESTAMP", os.environ.get("BUILD_TIME", "unknown")),
        "environment": "render" if os.environ.get("RENDER_SERVICE_ID") else "local",
    }


@app.get("/api/diagnostics/runtime")
def runtime_diagnostics() -> dict[str, Any]:
    """Non-secret diagnostics for packaged runtime activation and fallback."""
    return core.runtime_execution.diagnostics()


def _admin_actor(
    x_admin_role: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
    x_account_id: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> str:
    """Resolve the authenticated role at the HTTP boundary.

    Existing local installs have no account server and therefore default to
    the owner profile. Deployments can require an explicit identity with
    LUMINIFERA_REQUIRE_ADMIN_AUTH=1; ordinary roles are always rejected.
    """
    try:
        if authorization and authorization.lower().startswith("bearer "):
            session = core.auth.authenticate(authorization[7:].strip())
            return core.admin.authorize(session["role"], require_explicit=True)
        role = x_admin_role or x_user_role
        return core.admin.authorize_account(x_account_id, role, require_explicit=os.environ.get("LUMINIFERA_REQUIRE_ADMIN_AUTH") == "1")
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except AdminAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/admin/access")
def admin_access(actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    core.admin.touch_user("owner", display_name=str(core.settings.get("owner_display_name") or "Owner"), role=actor, organization_id=core.database.get_active_organization_id(), language=str(core.settings.get("interface_language") or "ru"))
    return {"allowed": True, "role": actor}


@app.post("/api/auth/login")
def auth_login(request: AuthLoginRequest) -> dict[str, Any]:
    try:
        controls = core.admin.advanced().get("controls", {})
        return core.auth.login(request.account_id, request.password, max_attempts=int(controls.get("rate_limit_per_minute", 60)))
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/api/auth/bootstrap", status_code=201)
def auth_bootstrap(request: AuthBootstrapRequest) -> dict[str, Any]:
    try:
        return core.auth.bootstrap_owner(request.account_id, request.display_name, request.password, language=request.language)
    except AuthenticationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/auth/register", status_code=201)
def auth_register(request: AuthRegisterRequest) -> dict[str, Any]:
    controls = core.admin.advanced().get("controls", {})
    if controls.get("registration_enabled") is not True:
        raise HTTPException(status_code=403, detail="registration_disabled")
    try:
        result = core.auth.register(request.account_id, request.display_name, request.password, language=request.language)
    except ValueError as exc:
        detail = str(exc)
        if detail == "account_already_exists":
            raise HTTPException(status_code=409, detail=detail) from exc
        raise HTTPException(status_code=422, detail=detail) from exc
    core.database.log_event("account_registered", json.dumps({"account_id": result["account_id"], "source": "public_auth"}))
    return result


@app.get("/api/auth/me")
def auth_me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="authentication_required")
    try:
        return core.auth.authenticate(authorization[7:].strip())
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/api/auth/logout")
def auth_logout(authorization: str | None = Header(default=None)) -> dict[str, bool]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="authentication_required")
    return {"revoked": core.auth.logout(authorization[7:].strip())}


@app.put("/api/auth/password")
def auth_password(request: AuthPasswordRequest, authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="authentication_required")
    try:
        return core.auth.change_password(authorization[7:].strip(), request.password)
    except (AuthenticationError, ValueError) as exc:
        raise HTTPException(status_code=401 if isinstance(exc, AuthenticationError) else 422, detail=str(exc)) from exc


@app.post("/api/telemetry")
def record_telemetry(request: TelemetryRequest, x_organization_id: str | None = Header(default=None), x_account_id: str | None = Header(default=None)) -> dict[str, str]:
    """Record a bounded product event for real analytics, without secrets."""
    organization_id = core.organization_id(x_organization_id)
    allowed = {"visit", "registration", "login", "session_started", "iris_opened", "constellation_opened", "goal_created", "goal_completed", "artifact_created", "evidence_created", "provider_call", "runtime_execution", "error", "fallback", "feedback_submitted"}
    if request.event_type not in allowed:
        raise HTTPException(status_code=422, detail="unsupported_telemetry_event")
    user_id = "".join(ch for ch in (x_account_id or request.user_id) if ch.isalnum() or ch in "._-")[:120] or "owner"
    core.admin.touch_user(user_id, display_name=user_id, role="member", organization_id=organization_id, language=str(core.settings.get("interface_language") or "ru"))
    event_id = core.database.record_product_telemetry(request.event_type, user_id=user_id, organization_id=organization_id, detail={"source": "product", "keys": sorted(str(key) for key in request.detail)[:20]})
    return {"event_id": event_id, "status": "recorded"}


@app.post("/api/usage")
def record_provider_usage(request: ProviderUsageRequest, x_account_id: str | None = Header(default=None)) -> dict[str, str]:
    account_id = x_account_id or request.account_id
    if core.provider_registry.get(request.provider_id) is None:
        raise HTTPException(status_code=404, detail="provider_not_found")
    core.admin.touch_user(account_id, display_name=account_id, role="member", organization_id=request.organization_id, language=str(core.settings.get("interface_language") or "ru"))
    cost, cost_status = request.cost, request.cost_status
    if cost is None and request.model_id:
        pricing = core.database.active_provider_pricing(request.provider_id, request.model_id)
        if pricing is not None:
            input_cost = (request.input_tokens or 0) * float(pricing["input_price_per_million"] or 0) / 1_000_000
            output_cost = (request.output_tokens or 0) * float(pricing["output_price_per_million"] or 0) / 1_000_000
            cost, cost_status = input_cost + output_cost, "known"
    usage_id = core.database.record_provider_usage(account_id=account_id, provider_id=request.provider_id, organization_id=request.organization_id, model_id=request.model_id, runtime=request.runtime, input_tokens=request.input_tokens, output_tokens=request.output_tokens, latency_ms=request.latency_ms, fallback=request.fallback, cost=cost, cost_status=cost_status if cost is not None else "unavailable")
    return {"usage_id": usage_id, "status": "recorded"}


@app.get("/api/admin/dashboard")
def admin_dashboard(period: str = Query(default="30d"), since: str | None = Query(default=None), until: str | None = Query(default=None), actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    try:
        return core.admin.dashboard(period, since=since, until=until)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/admin/analytics")
def admin_analytics(period: str = Query(default="30d"), since: str | None = Query(default=None), until: str | None = Query(default=None), actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    try:
        return core.admin.dashboard(period, since=since, until=until)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/admin/providers")
def admin_providers(actor: str = Depends(_admin_actor)) -> list[dict[str, Any]]:
    return core.admin.provider_read_model()


@app.post("/api/admin/providers/{provider_id}/check")
def admin_provider_check(provider_id: str, actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    profile = core.provider_registry.get(provider_id) or next((item for item in core.provider_registry.profiles() if item.display_name == provider_id), None)
    if profile is None:
        raise HTTPException(status_code=404, detail="provider_not_found")
    health = core.provider_health.check_provider(profile.provider_id)
    return {"name": profile.display_name, "state": health.health_status, "authentication": health.authentication_status, "available": health.health_status == "READY"}


@app.post("/api/admin/providers/{provider_id}/connect")
def admin_provider_connect(provider_id: str, request: ProviderConnectionRequest, actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    profile = core.provider_registry.get(provider_id) or next((item for item in core.provider_registry.profiles() if item.display_name == provider_id), None)
    if profile is None:
        raise HTTPException(status_code=404, detail="provider_not_found")
    try:
        core.provider_credentials.save(profile.provider_id, request.credential)
        health = core.provider_health.check_provider(profile.provider_id)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="provider_connection_failed") from exc
    return {"name": profile.display_name, "state": health.health_status, "available": health.health_status == "READY", "configured": True}


@app.post("/api/admin/providers/{provider_id}/disconnect")
def admin_provider_disconnect(provider_id: str, actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    profile = core.provider_registry.get(provider_id) or next((item for item in core.provider_registry.profiles() if item.display_name == provider_id), None)
    if profile is None:
        raise HTTPException(status_code=404, detail="provider_not_found")
    core.provider_credentials.remove(profile.provider_id)
    return {"name": profile.display_name, "state": "NOT_CONNECTED", "available": False, "configured": False}


@app.patch("/api/admin/providers/{provider_id}/policy")
def admin_provider_policy(provider_id: str, request: AdminProviderPolicyRequest, actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    try:
        if not core.admin.update_provider_policy(provider_id, **request.model_dump(), actor=actor):
            raise HTTPException(status_code=404, detail="provider_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return next(item for item in core.admin.provider_read_model() if item["id"] == provider_id)


@app.get("/api/admin/users")
def admin_users(query: str = Query(default="", max_length=120), actor: str = Depends(_admin_actor)) -> list[dict[str, Any]]:
    return core.admin.users(query)


@app.get("/api/admin/audit")
def admin_audit(limit: int = Query(default=100, ge=1, le=500), actor: str = Depends(_admin_actor)) -> list[dict[str, Any]]:
    return core.admin.audit(limit)


@app.get("/api/admin/advanced")
def admin_advanced(actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    return core.admin.advanced()


@app.patch("/api/admin/advanced")
def update_admin_advanced(request: AdminSettingsRequest, actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    try:
        return core.admin.save_advanced_controls(request.model_dump(exclude_none=True), actor)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/admin/health")
def admin_health(actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    return core.admin.health()


@app.get("/api/admin/security")
def admin_security(actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    return core.admin.security()


@app.get("/api/admin/plans")
def admin_plans(actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    return core.admin.plans()


@app.get("/api/admin/pricing")
def admin_pricing(actor: str = Depends(_admin_actor)) -> list[dict[str, Any]]:
    return core.admin.pricing()


@app.put("/api/admin/pricing")
def admin_save_pricing(request: PricingRequest, actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    try:
        return core.admin.save_pricing(request.model_dump(), actor)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/admin/users/{user_id}")
def admin_user_detail(user_id: str, actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    item = next((user for user in core.admin.users() if user["user_id"] == user_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="admin_user_not_found")
    return item


@app.patch("/api/admin/users/{user_id}")
def admin_account_update(user_id: str, request: AdminAccountRequest, actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    try:
        if not core.admin.update_account(user_id, actor, **request.model_dump()):
            raise HTTPException(status_code=404, detail="admin_user_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return next(item for item in core.admin.users() if item["account_id"] == user_id)


@app.put("/api/admin/users/{user_id}/credential")
def admin_set_credential(user_id: str, request: AdminCredentialRequest, actor: str = Depends(_admin_actor)) -> dict[str, str]:
    if not request.confirm:
        raise HTTPException(status_code=409, detail="confirmation_required")
    if not any(item["account_id"] == user_id for item in core.admin.users()):
        raise HTTPException(status_code=404, detail="admin_user_not_found")
    try:
        core.auth.set_password(user_id, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    core.database.log_event("admin_credential_changed", json.dumps({"actor": actor, "account_id": user_id}))
    with core.database.connect() as conn:
        conn.execute(
            "INSERT INTO management_audit_events (id, actor, object_type, object_id, action, new_value, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"ADMIN-{uuid.uuid4().hex[:12].upper()}", actor, "account_credential", user_id, "changed", '{"stored":"hash_only"}', "Credential write-only action"),
        )
    return {"account_id": user_id, "status": "credential_saved"}


@app.post("/api/admin/users/{user_id}/revoke-sessions")
def admin_revoke_sessions(user_id: str, request: AdminConfirmationRequest, actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    if not request.confirm:
        raise HTTPException(status_code=409, detail="confirmation_required")
    if not core.admin.update_account(user_id, actor, revoke_sessions=True):
        raise HTTPException(status_code=404, detail="admin_user_not_found")
    return {"account_id": user_id, "sessions": "revoked"}


@app.patch("/api/admin/users/{user_id}/status")
def admin_user_status(user_id: str, request: AdminUserStatusRequest, actor: str = Depends(_admin_actor)) -> dict[str, Any]:
    if not request.confirm:
        raise HTTPException(status_code=409, detail="confirmation_required")
    if not core.admin.set_user_status(user_id, request.status.upper(), actor):
        raise HTTPException(status_code=404, detail="admin_user_not_found")
    return {"user_id": user_id, "status": request.status.upper()}


@app.get("/api/session")
def session(x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    return {"organization_id": organization_id, "language": core.settings.get("interface_language", "ru")}


@app.post("/api/executions")
async def execute_runtime_neutral(
    request: ExecutionApiRequest,
    x_organization_id: str | None = Header(default=None),
    x_account_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Execute an Iris request through the runtime-neutral Product boundary."""
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_required")
    agents = list_chat_agents(core.database, organization_id=organization_id)
    if not agents:
        raise HTTPException(status_code=409, detail="team_required_before_execution")
    provider_id = str(core.settings.get("active_provider_id") or "")
    if request.preferred_runtime and core.provider_registry.get(request.preferred_runtime):
        provider_id = request.preferred_runtime
    if provider_id:
        try:
            core.admin.enforce_provider_policy(x_account_id or "owner", provider_id, model_id=str(core.settings.get("active_model_id") or "") or None)
        except PolicyDeniedError as exc:
            core.admin.audit_policy_denial(x_account_id or "owner", exc.reason, provider_id)
            raise HTTPException(status_code=429 if exc.reason.startswith("quota_exceeded") else 403, detail={"code": "execution_policy_denied", "reason": exc.reason}) from exc
    result = await asyncio.to_thread(
        core.iris_orchestration.execute,
        IrisExecutionContext(
            organization_id=organization_id,
            conversation_id=str(core.conversation_id(organization_id)),
        ),
        request.objective,
        agents,
        request.policy,
        preferred_runtime=request.preferred_runtime,
    )
    return {
        "ok": result.ok,
        "summary": result.summary,
        "runtime_id": result.runtime_id,
        "organization_id": result.organization_id,
        "correlation_id": result.correlation_id,
        "artifacts": list(result.artifact_refs),
        "evidence": list(result.evidence_refs),
        "data": dict(result.data),
        "events": [_plain(event) for event in result.events],
    }


@app.get("/api/organizations")
def organizations() -> list[dict[str, Any]]:
    return [_row(row) for row in core.database.list_organizations()]


@app.post("/api/organizations")
async def create_organization(request: OrganizationRequest) -> dict[str, Any]:
    organization = core.universal.create_organization(request.name, request.purpose)
    result = _plain(organization)
    await core.events.publish({"type": "organization.updated", "data": result})
    return result


@app.patch("/api/organizations/{organization_id}")
async def update_organization(organization_id: str, request: OrganizationUpdateRequest) -> dict[str, Any]:
    core.organization_id(organization_id)
    organization = core.universal.rename_organization(organization_id, request.name, request.purpose)
    result = _plain(organization)
    await core.events.publish({"type": "organization.updated", "data": result})
    return result


@app.get("/api/organizations/{organization_id}/home")
def home(organization_id: str) -> dict[str, Any]:
    core.organization_id(organization_id)
    return _plain(core.home.snapshot(organization_id))


@app.get("/api/organizations/{organization_id}/employees")
def employees(organization_id: str) -> list[dict[str, Any]]:
    core.organization_id(organization_id)
    return [_plain(agent) for agent in list_chat_agents(core.database, organization_id=organization_id)]


@app.get("/api/roles")
def roles() -> list[dict[str, Any]]:
    return [{"id": str(row["role_id"]), "name": str(row["display_name"] or row["role_id"]), "description": str(row["description"] or "")} for row in core.management.list_roles()]


@app.get("/api/organizations/{organization_id}/teams")
def teams(organization_id: str) -> list[dict[str, Any]]:
    core.organization_id(organization_id)
    return [_row(row) for row in core.database.list_organization_departments(organization_id)]


@app.get("/api/teams/templates")
def team_templates() -> list[dict[str, Any]]:
    return [_plain(item) for item in core.universal.list_templates()]


@app.post("/api/teams")
async def build_team(request: TeamRequest) -> dict[str, Any]:
    ready_provider = next(
        (profile.provider_id for profile in core.provider_registry.profiles()
         if core.provider_health.check_provider(profile.provider_id).health_status == "READY"),
        None,
    )
    result = core.universal.build_professional_team(
        request.brief,
        request.organization_name,
        template_id=request.template_id,
        team_size=request.team_size,
        provider_assignments={"*": ready_provider} if ready_provider else {},
    )
    payload = _plain(result)
    await core.events.publish({"type": "team.updated", "data": payload})
    return payload


@app.post("/api/organizations/{organization_id}/employees")
async def hire_employee(organization_id: str, request: EmployeeRequest) -> dict[str, Any]:
    core.organization_id(organization_id)
    agent_id = core.management.generate_agent_id(request.display_name)
    role_id = request.role_id.upper()
    permissions = sorted(ROLE_DEFAULT_PERMISSIONS.get(role_id, {"CHAT"}) | {"CHAT"})
    profile = AgentProfile(
        agent_id=agent_id,
        display_name=request.display_name.strip(),
        description=request.description.strip(),
        lifecycle_state="DRAFT" if request.provider_id == "UNAVAILABLE" else "ACTIVE",
        provider_id=request.provider_id,
        persona_id=f"{agent_id}-persona",
        full_name=request.display_name.strip(),
    )
    preview = core.management.create_agent(profile, [role_id], permissions, OWNER_ROLE, "Web hire")
    if not preview.ok:
        raise HTTPException(status_code=422, detail={"errors": preview.errors, "warnings": preview.warnings})
    core.database.create_organization_member(
        {
            "organization_id": organization_id,
            "agent_id": agent_id,
            "role_id": role_id,
            "position": request.display_name.strip(),
            "provider_id": request.provider_id,
            "permissions": permissions,
            "provisioning_status": "READY" if request.provider_id != "UNAVAILABLE" else "UNASSIGNED",
        }
    )
    employee = core.management.get_employee(agent_id)
    payload = _plain(employee) if employee is not None else {"agent_id": agent_id}
    await core.events.publish({"type": "employee.updated", "data": payload})
    return payload


@app.post("/api/organizations/{organization_id}/employees/{agent_id}/archive")
async def archive_employee(organization_id: str, agent_id: str) -> dict[str, str]:
    core.organization_id(organization_id)
    if agent_id not in core.database.list_organization_agent_ids(organization_id):
        raise HTTPException(status_code=404, detail="employee_not_found")
    core.management.archive_agent(agent_id, OWNER_ROLE, "Web archive")
    await core.events.publish({"type": "employee.updated", "data": {"agent_id": agent_id, "state": "ARCHIVED"}})
    return {"agent_id": agent_id, "state": "ARCHIVED"}


@app.patch("/api/organizations/{organization_id}/employees/{agent_id}/role")
async def reassign_employee_role(organization_id: str, agent_id: str, request: EmployeeRoleRequest) -> dict[str, Any]:
    core.organization_id(organization_id)
    if agent_id not in core.database.list_organization_agent_ids(organization_id):
        raise HTTPException(status_code=404, detail="employee_not_found")
    profile = core.database.get_agent_profile(agent_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="employee_not_found")
    role_id = request.role_id.upper()
    permissions = sorted(ROLE_DEFAULT_PERMISSIONS.get(role_id, {"CHAT"}) | {"CHAT"})
    preview = core.management.edit_agent(
        agent_id,
        display_name=str(profile["display_name"]),
        description=str(profile["description"] or ""),
        provider_id=str(profile["provider_id"]),
        persona_id=str(profile["persona_id"]) if profile["persona_id"] else None,
        roles=[role_id],
        permission_grants=permissions,
        permission_denies=core.database.list_agent_permission_denies(agent_id),
        expected_updated_at=str(profile["updated_at"]),
        avatar_path=str(profile["avatar_path"]) if profile["avatar_path"] else None,
        preferred_name=str(profile["preferred_name"] or ""),
        informal_name=str(profile["informal_name"] or ""),
        actor_role=OWNER_ROLE,
        reason="Web role reassignment",
    )
    if not preview.ok:
        raise HTTPException(status_code=422, detail={"errors": preview.errors, "warnings": preview.warnings})
    core.universal.reassign_member_role(organization_id, agent_id, role_id)
    employee = core.management.get_employee(agent_id)
    payload = _plain(employee) if employee is not None else {"agent_id": agent_id, "role_id": role_id}
    await core.events.publish({"type": "employee.updated", "data": payload})
    return payload


@app.delete("/api/organizations/{organization_id}/employees/{agent_id}")
async def delete_employee(organization_id: str, agent_id: str, confirm: bool = Query(default=False)) -> dict[str, str]:
    core.organization_id(organization_id)
    if not confirm:
        raise HTTPException(status_code=409, detail="confirmation_required")
    if agent_id not in core.database.list_organization_agent_ids(organization_id):
        raise HTTPException(status_code=404, detail="employee_not_found")
    core.management.delete_agent(agent_id, OWNER_ROLE, confirmed=True)
    await core.events.publish({"type": "employee.updated", "data": {"agent_id": agent_id, "state": "DELETED"}})
    return {"agent_id": agent_id, "state": "DELETED"}


@app.get("/api/chat")
def chat_history(x_organization_id: str | None = Header(default=None), limit: int = Query(default=80, ge=1, le=500)) -> list[dict[str, Any]]:
    organization_id = core.organization_id(x_organization_id)
    conversation_id = core.conversation_id(organization_id)
    attachments_by_message: dict[int, list[dict[str, Any]]] = {}
    for item in core.database.list_chat_attachments(conversation_id):
        message_id = item["message_id"]
        if message_id is None:
            continue
        attachments_by_message.setdefault(int(message_id), []).append({"id": str(item["id"]), "name": str(item["display_name"]), "media_type": str(item["media_type"]), "size": int(item["size"])})
    return [{**_plain(item), "attachments": attachments_by_message.get(item.id, [])} for item in core.database.list_messages(conversation_id, limit=limit)]


@app.post("/api/chat")
async def send_chat(request: ChatRequest, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    conversation_id = core.conversation_id(organization_id)
    message_id = core.database.add_message(conversation_id, "owner", request.content.strip())
    if request.attachment_ids:
        core.database.bind_chat_attachments(request.attachment_ids, message_id)
    await core.events.publish({"type": "iris.message", "data": {"id": message_id, "role": "owner", "content": request.content.strip()}})
    await core.events.publish({"type": "iris.state_changed", "data": {"state": "thinking", "organization_id": organization_id}})
    try:
        result = core.chat.handle(request.content, organization_id)
    except Exception:
        await core.events.publish({"type": "iris.state_changed", "data": {"state": "warning", "organization_id": organization_id}})
        raise
    response_message_id = None
    if result.message:
        response_message_id = core.database.add_message(conversation_id, "assistant", result.message)
        await core.events.publish({"type": "iris.message", "data": {"id": response_message_id, "role": "assistant", "content": result.message}})
    response = {"message_id": message_id, "response_message_id": response_message_id, "result": _plain(result)}
    await core.events.publish({"type": "iris.state_changed", "data": {"state": "complete", "organization_id": organization_id, "route": result.route}})
    await core.events.publish({"type": "organization.updated", "data": {"organization_id": organization_id, "action": result.action}})
    return response


@app.post("/api/chat/attachments")
async def upload_chat_attachment(file: UploadFile = File(...), x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="empty_attachment")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="attachment_too_large")
    attachment = core.attachments.import_bytes(
        core.conversation_id(organization_id), content, file.filename or "attachment", file.content_type or "application/octet-stream"
    )
    return {"id": attachment.attachment_id, "name": attachment.display_name, "media_type": attachment.media_type, "size": attachment.size}


@app.get("/api/chat/attachments/{attachment_id}")
def download_chat_attachment(attachment_id: str, x_organization_id: str | None = Header(default=None)) -> FileResponse:
    organization_id = core.organization_id(x_organization_id)
    conversation_id = core.conversation_id(organization_id)
    attachment = core.attachments.get_attachment(conversation_id, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="attachment_not_found")
    path = core.attachments.physical_path(attachment)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="attachment_file_not_found")
    return FileResponse(path, filename=attachment.display_name, media_type=attachment.media_type)


@app.get("/api/goals")
def goals(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    organization_id = core.organization_id(x_organization_id)
    return [_public_plan(plan) for plan in core.supervisor.list_plans(organization_id)]


@app.post("/api/goals")
async def create_goal(request: GoalRequest, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_required")
    try:
        plan = core.supervisor.director(organization_id, request.objective)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    result = _public_plan(plan)
    await core.events.publish({"type": "goal.created", "data": result})
    return result


def _goal_for_scope(plan_id: str, organization_id: str | None) -> Any:
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_required")
    plan = core.supervisor.get_plan(plan_id)
    if str(plan.organization_id) != organization_id:
        raise HTTPException(status_code=404, detail="goal_not_found")
    return plan


@app.get("/api/goals/{plan_id}")
def goal_detail(plan_id: str, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    """Return one organization-scoped goal for the Work product view."""
    return _public_plan(_goal_for_scope(plan_id, core.organization_id(x_organization_id)))


@app.post("/api/goals/{plan_id}/approve")
async def approve_goal(plan_id: str, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    _goal_for_scope(plan_id, organization_id)
    result = _public_plan(core.supervisor.approve(plan_id))
    await core.events.publish({"type": "goal.started", "data": result})
    return result


@app.post("/api/goals/{plan_id}/replan")
async def replan_goal(plan_id: str, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    _goal_for_scope(plan_id, organization_id)
    result = _public_plan(core.supervisor.replan(plan_id))
    await core.events.publish({"type": "goal.progressed", "data": result})
    return result


@app.post("/api/goals/{plan_id}/retry")
async def retry_goal(plan_id: str, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    _goal_for_scope(plan_id, organization_id)
    result = _public_plan(core.supervisor.replan(plan_id))
    await core.events.publish({"type": "goal.progressed", "data": result})
    return result


@app.post("/api/goals/{plan_id}/cancel")
async def cancel_goal(plan_id: str, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    _goal_for_scope(plan_id, organization_id)
    result = _public_plan(core.supervisor.cancel(plan_id))
    await core.events.publish({"type": "goal.blocked", "data": result})
    return result


_TRACE_EVENT_TYPES = {
    "work_item_running": "work.started",
    "tool_observed": "work.progressed",
    "artifact_created": "artifact.created",
    "review_requested": "review.started",
    "review_rework_requested": "review.rework_requested",
    "review_passed": "review.passed",
    "work_item_finished": "work.completed",
}


async def _publish_runtime_trace(organization_id: str, plan_id: str, state: Any, seen: set[str]) -> None:
    for trace in sorted(state.trace_events.values(), key=lambda item: item.created_at):
        if trace.event_id in seen:
            continue
        seen.add(trace.event_id)
        event_type = next(
            (mapped for stage, mapped in _TRACE_EVENT_TYPES.items() if trace.stage.startswith(stage)),
            None,
        )
        if event_type is None:
            continue
        await core.events.publish({
            "type": event_type,
            "data": {
                "organization_id": organization_id,
                "plan_id": plan_id,
                "goal_id": trace.goal_id,
                "work_item_id": trace.work_item_id,
                "action_id": trace.action_id,
                "observation_id": trace.observation_id,
                "artifact_id": trace.artifact_id,
                "detail": trace.detail,
            },
        })


async def _run_goal_with_events(organization_id: str, plan_id: str, goal: str, agents: list[Any]) -> Any:
    """Run Core work off the event loop while forwarding durable checkpoint traces."""
    run = asyncio.create_task(asyncio.to_thread(core.runtime_v3.run_goal, organization_id, goal, agents))
    checkpoint = core.workspace_root / "runtime_v3_goals" / organization_id / "checkpoints" / "state.json"
    seen: set[str] = set()
    while not run.done():
        try:
            if checkpoint.is_file():
                await _publish_runtime_trace(organization_id, plan_id, load_state(checkpoint), seen)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            pass
        await asyncio.sleep(0.1)
    result = await run
    await _publish_runtime_trace(organization_id, plan_id, result.state, seen)
    return result


@app.post("/api/goals/{plan_id}/start")
async def start_goal(plan_id: str, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    plan = _goal_for_scope(plan_id, organization_id)
    agents = list_chat_agents(core.database, organization_id=organization_id)
    if not agents:
        raise HTTPException(status_code=409, detail="team_required_before_goal_start")
    await core.events.publish({"type": "goal.started", "data": {"plan_id": plan_id, "goal": plan.goal}})
    result = await _run_goal_with_events(organization_id, plan_id, plan.goal, agents)
    payload = {
        "ok": result.ok,
        "summary": result.summary,
        "work_items": len(result.state.work_items),
        "artifacts": len(result.state.artifacts),
        "evidence": len(result.state.evidence),
        "findings": len(result.state.findings),
        "receipt_ready": bool(result.state.work_receipts),
    }
    await core.events.publish({"type": "goal.completed" if result.ok else "goal.blocked", "data": payload})
    return payload


@app.get("/api/work")
def work(x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    return _plain(core.work.snapshot(core.organization_id(x_organization_id)))


@app.get("/api/work/receipt")
def work_receipt(x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    return _plain(core.work.receipt(core.organization_id(x_organization_id)))


@app.get("/api/work/items")
def work_items(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    return [_plain(item) for item in core.work.items(core.organization_id(x_organization_id))]


@app.get("/api/work/review")
def work_review(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    return [_plain(item) for item in core.work.review_findings(core.organization_id(x_organization_id))]


@app.get("/api/work/timeline")
def work_timeline(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    return [_plain(item) for item in core.work.timeline(core.organization_id(x_organization_id))]


@app.get("/api/files")
def files(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    return [_plain(item) for item in core.files.list_files(core.organization_id(x_organization_id))]


def _file_path_for_scope(file_id: str, organization_id: str | None) -> Path:
    """Resolve a product file from either the durable DB or Runtime V3 state."""
    if not organization_id:
        raise HTTPException(status_code=404, detail="file_not_found")
    try:
        artifact = _artifact_for_scope(file_id, organization_id)
    except HTTPException:
        artifact = None
    if artifact is not None:
        return _artifact_path(artifact)
    path = core.files.runtime_artifact_path(organization_id, file_id)
    if path is None:
        raise HTTPException(status_code=404, detail="file_not_found")
    return path


@app.get("/api/files/{file_id}/preview")
def file_preview(file_id: str, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    path = _file_path_for_scope(file_id, core.organization_id(x_organization_id))
    if path.suffix.lower() not in {".txt", ".md", ".json", ".csv", ".log"}:
        return {"kind": "binary", "title": path.name, "preview": ""}
    return {"kind": "text", "title": path.name, "preview": path.read_text(encoding="utf-8", errors="replace")[:50_000]}


@app.get("/api/files/{file_id}/download")
def file_download(file_id: str, x_organization_id: str | None = Header(default=None)) -> FileResponse:
    path = _file_path_for_scope(file_id, core.organization_id(x_organization_id))
    return FileResponse(path, filename=path.name)


@app.get("/api/artifacts")
def artifacts(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        return []
    return [_row(row) for row in core.database.list_artifacts(limit=100, organization_id=organization_id)]


def _artifact_for_scope(artifact_id: str, organization_id: str | None) -> Any:
    artifact = core.database.get_artifact(artifact_id)
    if artifact is None or not organization_id:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    task_id = str(artifact["task_id"] or "")
    task = core.database.get_task(task_id) if task_id else None
    if task is not None and str(task["organization_id"] or "") != organization_id:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    return artifact


def _artifact_path(artifact: Any) -> Path:
    try:
        return PathGuard(core.workspace_root).resolve_safe_path(str(artifact["relative_path"] or ""))
    except PathGuardError as exc:
        raise HTTPException(status_code=400, detail="artifact_path_invalid") from exc


@app.get("/api/artifacts/{artifact_id}/preview")
def artifact_preview(artifact_id: str, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    artifact = _artifact_for_scope(artifact_id, core.organization_id(x_organization_id))
    path = _artifact_path(artifact)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="artifact_file_not_found")
    if path.suffix.lower() not in {".txt", ".md", ".json", ".csv", ".log"}:
        return {"kind": "binary", "title": path.name, "preview": ""}
    return {"kind": "text", "title": path.name, "preview": path.read_text(encoding="utf-8", errors="replace")[:50_000]}


@app.get("/api/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str, x_organization_id: str | None = Header(default=None)) -> FileResponse:
    artifact = _artifact_for_scope(artifact_id, core.organization_id(x_organization_id))
    path = _artifact_path(artifact)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="artifact_file_not_found")
    return FileResponse(path, filename=path.name, media_type=str(artifact["media_type"] or "application/octet-stream"))


@app.get("/api/providers")
def providers() -> list[dict[str, Any]]:
    labels = {
        "READY": "Ready",
        "AUTHENTICATION_REQUIRED": "Login required",
        "NOT_AUTHENTICATED": "Login required",
        "BUSY": "Busy",
        "ERROR": "Error",
    }
    result = []
    for profile in core.provider_registry.profiles():
        health = core.provider_health.latest_health(profile.provider_id)
        adapter = core.provider_adapters.get(profile.provider_id)
        capability_profile = getattr(adapter, "capability_profile", None)
        raw_state = health.health_status if health is not None else "UNAVAILABLE"
        result.append({
            "id": profile.provider_id,
            "name": profile.display_name,
            "state": labels.get(raw_state, "Unavailable"),
            "available": raw_state == "READY",
            "configured": core.provider_credentials.is_configured(profile.provider_id),
            "model_id": str(getattr(capability_profile, "model_id", "") or ""),
        })
    return result


@app.post("/api/providers/{provider_id}/check")
async def check_provider(provider_id: str) -> dict[str, Any]:
    if core.provider_registry.get(provider_id) is None:
        raise HTTPException(status_code=404, detail="provider_not_found")
    health = core.provider_health.check_provider(provider_id)
    state = "Ready" if health.health_status == "READY" else "Login required" if health.authentication_status in {"NOT_AUTHENTICATED", "AUTHENTICATION_REQUIRED"} else "Unavailable"
    payload = {"id": provider_id, "state": state, "available": health.health_status == "READY"}
    await core.events.publish({"type": "provider.updated", "data": payload})
    return payload


@app.post("/api/providers/{provider_id}/connect")
def connect_provider(provider_id: str, request: ProviderConnectionRequest) -> dict[str, Any]:
    profile = core.provider_registry.get(provider_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="provider_not_found")
    try:
        core.provider_credentials.save(provider_id, request.credential)
        health = core.provider_health.check_provider(provider_id)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail="provider_connection_failed") from exc
    ready = health.health_status == "READY"
    payload = {"id": provider_id, "name": profile.display_name, "state": "Ready" if ready else "Connected, verification required", "available": ready, "configured": True}
    return payload


@app.post("/api/providers/{provider_id}/disconnect")
def disconnect_provider(provider_id: str) -> dict[str, Any]:
    profile = core.provider_registry.get(provider_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="provider_not_found")
    core.provider_credentials.remove(provider_id)
    health = core.provider_health.check_provider(provider_id)
    return {"id": provider_id, "name": profile.display_name, "state": "Login required", "available": False, "configured": False}


@app.post("/api/feedback")
def create_feedback(request: FeedbackRequest, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_required")
    category = request.category.strip().lower()
    if category not in {"bug", "ux", "feature", "confusion", "performance", "praise", "other"}:
        raise HTTPException(status_code=422, detail="unsupported_feedback_category")
    feedback_id = f"feedback-{uuid.uuid4().hex[:12]}"
    core.database.create_feedback(feedback_id, organization_id, category, request.description.strip())
    core.database.log_event("feedback_created", f"{feedback_id}:{category}")
    return {"id": feedback_id, "category": category, "status": "NEW", "created_at": "now"}


@app.get("/api/feedback")
def feedback(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        return []
    return [_row(row) for row in core.database.list_feedback(organization_id)]


@app.get("/api/diagnostics")
def diagnostics(x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    return {
        "product": "Luminifera",
        "version": app.version,
        "organization_id": organization_id,
        "services": {"api": "ready", "database": "ready", "runtime": "available"},
        "providers": providers(),
        "known_limitations": ["Состояние провайдера зависит от установленного CLI и доступной авторизации."],
        "privacy": "Секреты, cookies и содержимое чата в диагностический ответ не включаются.",
    }


@app.get("/api/skills")
def skills(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        return []
    return [
        {"id": item.skill_id, "name": item.name, "purpose": item.purpose, "status": item.status, "version": item.version, "roles": item.supported_roles}
        for item in core.skills.list_packages(organization_id)
    ]


def _skill_for_scope(skill_id: str, organization_id: str | None) -> Any:
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_required")
    skill = next((item for item in core.skills.list_packages(organization_id) if item.skill_id == skill_id), None)
    if skill is None:
        raise HTTPException(status_code=404, detail="skill_not_found")
    return skill


@app.post("/api/skills")
async def create_skill(request: SkillPackageRequest, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_required")
    try:
        skill_id = core.skills.create_package(
            name=request.name,
            purpose=request.purpose,
            supported_roles=[role.upper() for role in request.supported_roles],
            instructions=request.instructions,
            tools=request.tools,
            version=request.version,
            organization_id=organization_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    skill = _skill_for_scope(skill_id, organization_id)
    payload = {"id": skill.skill_id, "name": skill.name, "purpose": skill.purpose, "status": skill.status, "version": skill.version, "roles": skill.supported_roles}
    await core.events.publish({"type": "skill.updated", "data": {"organization_id": organization_id, **payload}})
    return payload


@app.patch("/api/skills/{skill_id}/status")
async def update_skill_status(skill_id: str, request: SkillStatusRequest, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    _skill_for_scope(skill_id, organization_id)
    try:
        core.skills.update_status(skill_id, request.status.upper(), reason=request.reason, organization_id=organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    skill = _skill_for_scope(skill_id, organization_id)
    payload = {"id": skill.skill_id, "name": skill.name, "purpose": skill.purpose, "status": skill.status, "version": skill.version, "roles": skill.supported_roles}
    await core.events.publish({"type": "skill.updated", "data": {"organization_id": organization_id, **payload}})
    return payload


@app.get("/api/knowledge")
def knowledge(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        return []
    return [
        {
            "id": item.entry_id,
            "title": item.title,
            "summary": item.content,
            "status": item.lifecycle_state,
            "source": item.source_employee_name,
            "verified": item.lifecycle_state == "VERIFIED",
        }
        for item in core.competence.list_memory(organization_id)
    ]


def _memory_for_scope(entry_id: str, organization_id: str | None) -> Any:
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_required")
    memory = next((item for item in core.competence.list_memory(organization_id) if item.entry_id == entry_id), None)
    if memory is None:
        raise HTTPException(status_code=404, detail="knowledge_not_found")
    return memory


def _run_belongs_to_scope(run_id: str, organization_id: str | None) -> None:
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_required")
    run = core.database.get_agent_run(run_id)
    if run is None or str(run["agent_id"] or "") not in core.database.list_organization_agent_ids(organization_id):
        raise HTTPException(status_code=404, detail="run_not_found")


@app.post("/api/knowledge")
async def propose_knowledge(request: KnowledgeProposalRequest, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    _run_belongs_to_scope(request.source_run_id, organization_id)
    try:
        memory = core.competence.propose_knowledge(
            organization_id=organization_id,
            source_run_id=request.source_run_id,
            competence=request.competence,
            title=request.title,
            content=request.content,
            outcome=request.outcome,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    payload = {"id": memory.entry_id, "title": memory.title, "summary": memory.content, "status": memory.lifecycle_state, "source": memory.source_employee_name, "verified": memory.lifecycle_state == "VERIFIED"}
    await core.events.publish({"type": "knowledge.updated", "data": {"organization_id": organization_id, **payload}})
    return payload


@app.post("/api/knowledge/{entry_id}/verify")
async def verify_knowledge(entry_id: str, request: KnowledgeVerifyRequest, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    _memory_for_scope(entry_id, organization_id)
    _run_belongs_to_scope(request.review_run_id, organization_id)
    try:
        memory, node = core.competence.verify_knowledge(entry_id, request.review_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    payload = {"id": memory.entry_id, "title": memory.title, "summary": memory.content, "status": memory.lifecycle_state, "source": memory.source_employee_name, "verified": memory.lifecycle_state == "VERIFIED", "competence": {"id": node.node_id, "name": node.competence, "growth_points": node.growth_points}}
    await core.events.publish({"type": "knowledge.updated", "data": {"organization_id": organization_id, **payload}})
    await core.events.publish({"type": "competence.updated", "data": {"organization_id": organization_id, "id": node.node_id, "growth_points": node.growth_points}})
    return payload


@app.get("/api/competence")
def competence(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        return []
    return [
        {
            "id": item.node_id,
            "employee": item.employee_name,
            "competence": item.competence,
            "growth_points": item.growth_points,
            "status": item.lifecycle_state,
        }
        for item in core.competence.list_competence(organization_id)
    ]


@app.get("/api/settings")
def settings() -> dict[str, Any]:
    return {key: core.settings.get(key) for key in (
        "interface_language", "theme", "message_sounds_enabled", "reduce_motion",
        "developer_mode", "owner_display_name", "user_avatar_path",
        "active_provider_id", "active_model_id", "onboarding_skipped",
    )}


@app.patch("/api/settings")
def update_settings(request: SettingsRequest) -> dict[str, Any]:
    values = request.model_dump(exclude_none=True)
    if "interface_language" in values and values["interface_language"] not in {"ru", "uk", "en"}:
        raise HTTPException(status_code=422, detail="unsupported_language")
    if values.get("active_provider_id") and core.provider_registry.get(values["active_provider_id"]) is None:
        raise HTTPException(status_code=422, detail="unsupported_provider")
    core.settings.update(values)
    core._save_settings(core.settings)
    return settings()


@app.get("/api/profile")
def profile() -> dict[str, Any]:
    avatar = str(core.settings.get("user_avatar_path", "") or "")
    return {
        "display_name": str(core.settings.get("owner_display_name", "Владелец") or "Владелец"),
        "avatar": Path(avatar).name if avatar else "",
    }


@app.get("/api/profile/avatars")
def profile_avatars() -> list[dict[str, str]]:
    return [{"name": path.name, "url": f"/api/profile/avatars/{path.name}"} for path in list_avatar_files(core.paths.avatar_dir)]


@app.get("/api/profile/avatars/{avatar_name}")
def profile_avatar(avatar_name: str) -> FileResponse:
    candidates = [path for path in list_avatar_files(core.paths.avatar_dir) if path.name == avatar_name]
    if not candidates:
        raise HTTPException(status_code=404, detail="avatar_not_found")
    return FileResponse(candidates[0])


@app.patch("/api/profile")
def update_profile(request: ProfileRequest) -> dict[str, Any]:
    avatar = request.avatar.strip()
    if avatar and not any(path.name == avatar for path in list_avatar_files(core.paths.avatar_dir)):
        raise HTTPException(status_code=422, detail="avatar_not_found")
    core.settings["owner_display_name"] = " ".join(request.display_name.split())
    core.settings["user_avatar_path"] = str(core.paths.avatar_dir / avatar) if avatar else ""
    core._save_settings(core.settings)
    return profile()


@app.get("/api/profile/backup")
def download_profile_backup() -> FileResponse:
    """Create a secret-free portable profile backup through the Core service."""
    output = core.paths.data_dir / "web-backups" / "luminifera-profile.zip"
    try:
        core.backups.backup(core.paths.user_dir, output)
    except (OSError, ProfileBackupError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="backup_failed") from exc
    return FileResponse(output, filename="luminifera-profile.zip", media_type="application/zip")


@app.get("/api/iris")
def iris(x_organization_id: str | None = Header(default=None)) -> dict[str, str]:
    organization_id = core.organization_id(x_organization_id)
    state = "idle"
    message = "Опишите результат, и Iris поможет превратить его в реальную работу."
    if organization_id:
        plans = core.supervisor.list_plans(organization_id)
        active = next((plan for plan in reversed(plans) if plan.status not in {"COMPLETED", "CANCELLED"}), None)
        if active is not None:
            state = {
                "AWAITING_OWNER_APPROVAL": "waiting_for_user",
                "IN_PROGRESS": "working",
                "NEEDS_STAFFING": "attention",
                "BLOCKED": "warning",
                "READY": "planning",
            }.get(active.status, "listening")
            message = active.summary or f"Текущая цель: {active.goal}"
    return {"name": "Iris", "state": state, "message": message}
    return {"name": "Iris", "state": "idle", "message": "Опишите результат, и я помогу превратить его в реальную работу."}


@app.websocket("/api/events")
async def events(socket: WebSocket, organization_id: str | None = None) -> None:
    scoped_organization_id = core.organization_id(organization_id)
    await core.events.add(socket, scoped_organization_id)
    try:
        while True:
            await socket.receive_text()
    except WebSocketDisconnect:
        core.events.remove(socket)
    except Exception:
        core.events.remove(socket)


STATIC = ROOT / "apps" / "web" / "static"
if STATIC.is_dir():
    # Product pages reference both legacy root assets and the V3 shell under
    # /assets/v3/*; mounting the static root keeps both paths valid on Render.
    app.mount("/assets", StaticFiles(directory=STATIC), name="assets")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/app", include_in_schema=False)
@app.get("/app/", include_in_schema=False)
def workspace_app() -> FileResponse:
    return FileResponse(STATIC / "app.html")


@app.get("/runtime-config.js", include_in_schema=False)
def runtime_config() -> Response:
    """Keep the browser bridge same-origin in the hosted deployment."""
    return Response("window.LUMINIFERA_API_BASE = '';\n", media_type="application/javascript")
