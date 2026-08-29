from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.agent_directory import list_chat_agents
from core.config_repository import ConfigurationRepository
from core.database import Database
from core.luminifera_files_service import LuminiferaFilesService
from core.luminifera_home_service import LuminiferaHomeService
from core.luminifera_work_service import LuminiferaWorkService
from core.management_service import ManagementService
from core.settings_service import SettingsService
from core.supervisor_application_service import SupervisorApplicationService
from core.supervisor_chat_service import SupervisorChatApplicationService
from core.universal_platform_service import UniversalPlatformService


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)


class OrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    purpose: str = Field(default="", max_length=2_000)


class GoalRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=10_000)


class SettingsRequest(BaseModel):
    interface_language: str | None = None
    theme: str | None = None
    message_sounds_enabled: bool | None = None


class ConnectionHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def add(self, socket: WebSocket) -> None:
        await socket.accept()
        self._clients.add(socket)

    def remove(self, socket: WebSocket) -> None:
        self._clients.discard(socket)

    async def publish(self, event: dict[str, Any]) -> None:
        payload = json.dumps(event, ensure_ascii=False)
        stale: list[WebSocket] = []
        for socket in tuple(self._clients):
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


core = WebCore()
app = FastAPI(title="Luminifera API", version="0.1.0", docs_url="/api/docs", redoc_url="/api/redoc")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ready", "product": "Luminifera", "engine": "Python Core / Runtime V3"}


@app.get("/api/session")
def session(x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    return {"organization_id": organization_id, "language": core.settings.get("interface_language", "ru")}


@app.get("/api/organizations")
def organizations() -> list[dict[str, Any]]:
    return [_row(row) for row in core.database.list_organizations()]


@app.post("/api/organizations")
async def create_organization(request: OrganizationRequest) -> dict[str, Any]:
    organization = core.universal.create_organization(request.name, request.purpose)
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


@app.get("/api/organizations/{organization_id}/teams")
def teams(organization_id: str) -> list[dict[str, Any]]:
    core.organization_id(organization_id)
    return [_row(row) for row in core.database.list_organization_departments(organization_id)]


@app.get("/api/chat")
def chat_history(x_organization_id: str | None = Header(default=None), limit: int = Query(default=80, ge=1, le=500)) -> list[dict[str, Any]]:
    organization_id = core.organization_id(x_organization_id)
    return [_plain(item) for item in core.database.list_messages(core.conversation_id(organization_id), limit=limit)]


@app.post("/api/chat")
async def send_chat(request: ChatRequest, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    conversation_id = core.conversation_id(organization_id)
    message_id = core.database.add_message(conversation_id, "owner", request.content.strip())
    await core.events.publish({"type": "iris.message", "data": {"id": message_id, "role": "owner", "content": request.content.strip()}})
    result = core.chat.handle(request.content, organization_id)
    response_message_id = None
    if result.message:
        response_message_id = core.database.add_message(conversation_id, "assistant", result.message)
        await core.events.publish({"type": "iris.message", "data": {"id": response_message_id, "role": "assistant", "content": result.message}})
    response = {"message_id": message_id, "response_message_id": response_message_id, "result": _plain(result)}
    await core.events.publish({"type": "organization.updated", "data": {"organization_id": organization_id, "action": result.action}})
    return response


@app.get("/api/goals")
def goals(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    organization_id = core.organization_id(x_organization_id)
    return [_plain(plan) for plan in core.supervisor.list_plans(organization_id)]


@app.post("/api/goals")
async def create_goal(request: GoalRequest, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_required")
    plan = core.supervisor.director(organization_id, request.objective)
    result = _plain(plan)
    await core.events.publish({"type": "goal.created", "data": result})
    return result


def _goal_for_scope(plan_id: str, organization_id: str | None) -> Any:
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_required")
    plan = core.supervisor.get_plan(plan_id)
    if str(plan.organization_id) != organization_id:
        raise HTTPException(status_code=404, detail="goal_not_found")
    return plan


@app.post("/api/goals/{plan_id}/approve")
async def approve_goal(plan_id: str, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    _goal_for_scope(plan_id, organization_id)
    result = _plain(core.supervisor.approve(plan_id))
    await core.events.publish({"type": "goal.started", "data": result})
    return result


@app.post("/api/goals/{plan_id}/replan")
async def replan_goal(plan_id: str, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    _goal_for_scope(plan_id, organization_id)
    result = _plain(core.supervisor.replan(plan_id))
    await core.events.publish({"type": "goal.progressed", "data": result})
    return result


@app.post("/api/goals/{plan_id}/cancel")
async def cancel_goal(plan_id: str, x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    organization_id = core.organization_id(x_organization_id)
    _goal_for_scope(plan_id, organization_id)
    result = _plain(core.supervisor.cancel(plan_id))
    await core.events.publish({"type": "goal.blocked", "data": result})
    return result


@app.get("/api/work")
def work(x_organization_id: str | None = Header(default=None)) -> dict[str, Any]:
    return _plain(core.work.snapshot(core.organization_id(x_organization_id)))


@app.get("/api/files")
def files(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    return [_plain(item) for item in core.files.list_files(core.organization_id(x_organization_id))]


@app.get("/api/artifacts")
def artifacts(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        return []
    return [_row(row) for row in core.database.list_artifacts(limit=100, organization_id=organization_id)]


@app.get("/api/providers")
def providers() -> list[dict[str, Any]]:
    return [_row(row) for row in core.database.list_provider_definitions()]


@app.get("/api/skills")
def skills(x_organization_id: str | None = Header(default=None)) -> list[dict[str, Any]]:
    organization_id = core.organization_id(x_organization_id)
    if not organization_id:
        return []
    return [_row(row) for row in core.database.list_skill_packages(organization_id)]


@app.get("/api/knowledge")
def knowledge() -> list[dict[str, Any]]:
    return [_row(row) for row in core.database.list_knowledge_cards()]


@app.get("/api/settings")
def settings() -> dict[str, Any]:
    return {key: core.settings.get(key) for key in ("interface_language", "theme", "message_sounds_enabled", "reduce_motion")}


@app.patch("/api/settings")
def update_settings(request: SettingsRequest) -> dict[str, Any]:
    values = request.model_dump(exclude_none=True)
    if "interface_language" in values and values["interface_language"] not in {"ru", "uk", "en"}:
        raise HTTPException(status_code=422, detail="unsupported_language")
    core.settings.update(values)
    core._save_settings(core.settings)
    return settings()


@app.get("/api/iris")
def iris() -> dict[str, str]:
    return {"name": "Iris", "state": "idle", "message": "Опишите результат, и я помогу превратить его в реальную работу."}


@app.websocket("/api/events")
async def events(socket: WebSocket) -> None:
    await core.events.add(socket)
    try:
        while True:
            await socket.receive_text()
    except WebSocketDisconnect:
        core.events.remove(socket)
    except Exception:
        core.events.remove(socket)


STATIC = ROOT / "apps" / "web" / "static"
if STATIC.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
