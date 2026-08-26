from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import Action, ActionType, Observation, ObservationStatus, new_id


@dataclass(frozen=True)
class ToolDefinition:
    """MCP-style local tool declaration, independent of a provider prompt."""

    name: str
    action_type: ActionType
    required_permission: str
    required_provider_capability: str
    input_schema: dict[str, object]


class ToolRegistry:
    def __init__(self, definitions: list[ToolDefinition] | None = None) -> None:
        self._by_action = {definition.action_type: definition for definition in definitions or self.default_definitions()}

    @staticmethod
    def default_definitions() -> list[ToolDefinition]:
        path_schema = {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}
        return [
            ToolDefinition("workspace.read", ActionType.FILESYSTEM_READ, "READ_WORKSPACE", "filesystem.read", path_schema),
            ToolDefinition("workspace.list", ActionType.FILESYSTEM_LIST, "READ_WORKSPACE", "filesystem.read", path_schema),
            ToolDefinition("workspace.write", ActionType.FILESYSTEM_WRITE, "WRITE_WORKSPACE", "filesystem.write", {"type": "object", "required": ["path", "content"]}),
        ]

    def definition_for(self, action_type: ActionType) -> ToolDefinition | None:
        return self._by_action.get(action_type)

    def negotiate(self, employee_id: str, requested: list[ActionType], permissions: set[str] | None, provider_capabilities: set[str] | None) -> tuple[list[ToolDefinition], list[str]]:
        granted: list[ToolDefinition] = []
        denied: list[str] = []
        for action_type in requested:
            definition = self.definition_for(action_type)
            if definition is None:
                denied.append(f"unsupported:{action_type}")
            elif permissions is not None and definition.required_permission not in permissions:
                denied.append(f"permission:{definition.name}")
            elif provider_capabilities and definition.required_provider_capability not in provider_capabilities:
                denied.append(f"provider_capability:{definition.name}")
            else:
                granted.append(definition)
        return granted, denied


class ToolRuntime:
    """Minimal generic tool runtime returning typed observations."""

    def __init__(self, workspace_root: Path, employee_permissions: dict[str, set[str]] | None = None, employee_provider_capabilities: dict[str, set[str]] | None = None, registry: ToolRegistry | None = None) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.employee_permissions = employee_permissions or {}
        self.employee_provider_capabilities = employee_provider_capabilities or {}
        self.registry = registry or ToolRegistry()

    def negotiate(self, employee_id: str, requested: list[ActionType]) -> tuple[list[ToolDefinition], list[str]]:
        return self.registry.negotiate(
            employee_id, requested, self.employee_permissions.get(employee_id), self.employee_provider_capabilities.get(employee_id),
        )

    def execute(self, action: Action) -> Observation:
        try:
            _granted, denied = self.negotiate(action.employee_id, [action.action_type])
            if denied:
                label = "permission denied" if denied[0].startswith("permission:") else "tool negotiation denied"
                return Observation(new_id("obs"), action.action_id, ObservationStatus.FAILED, f"{label}: {denied[0]}")
            if action.action_type == ActionType.FILESYSTEM_WRITE:
                return self._write(action)
            if action.action_type == ActionType.FILESYSTEM_READ:
                return self._read(action)
            if action.action_type == ActionType.FILESYSTEM_LIST:
                return self._list(action)
        except Exception as exc:
            return Observation(new_id("obs"), action.action_id, ObservationStatus.FAILED, f"{type(exc).__name__}: {exc}")
        return Observation(new_id("obs"), action.action_id, ObservationStatus.UNSUPPORTED, f"Unsupported tool: {action.action_type}")

    def execute_terminal(self, action: Action) -> Observation:
        permissions = self.employee_permissions.get(action.employee_id)
        if permissions is not None and "RUN_COMMANDS" not in permissions:
            return Observation(new_id("obs"), action.action_id, ObservationStatus.FAILED, "permission denied: RUN_COMMANDS")
        command = str(action.payload.get("command", "")).strip()
        if not command:
            return Observation(new_id("obs"), action.action_id, ObservationStatus.FAILED, "empty command")
        completed = subprocess.run(command, cwd=self.workspace_root, text=True, capture_output=True, shell=True, timeout=30)
        return Observation(
            new_id("obs"),
            action.action_id,
            ObservationStatus.OK if completed.returncode == 0 else ObservationStatus.FAILED,
            f"exit={completed.returncode}",
            {"stdout": completed.stdout, "stderr": completed.stderr, "returncode": completed.returncode},
        )

    def _resolve(self, raw_path: str) -> Path:
        path = (self.workspace_root / raw_path).resolve()
        if self.workspace_root not in path.parents and path != self.workspace_root:
            raise ValueError("path escapes workspace")
        return path

    def _write(self, action: Action) -> Observation:
        path = self._resolve(str(action.payload["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(action.payload.get("content", ""))
        path.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return Observation(
            new_id("obs"),
            action.action_id,
            ObservationStatus.OK,
            f"wrote {path.name}",
            {"path": str(path), "sha256": digest, "bytes": len(content.encode("utf-8"))},
        )

    def _read(self, action: Action) -> Observation:
        path = self._resolve(str(action.payload["path"]))
        content = path.read_text(encoding="utf-8")
        return Observation(
            new_id("obs"),
            action.action_id,
            ObservationStatus.OK,
            f"read {path.name}",
            {"path": str(path), "content": content, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()},
        )

    def _list(self, action: Action) -> Observation:
        path = self._resolve(str(action.payload.get("path", ".")))
        entries = sorted(item.name for item in path.iterdir())
        return Observation(new_id("obs"), action.action_id, ObservationStatus.OK, f"listed {path.name}", {"path": str(path), "entries": entries})
