from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol


@dataclass(frozen=True)
class ProviderExecutionRequest:
    runtime_task_id: str
    goal: str
    filename: str
    content: str
    physical_workspace: Path


@dataclass(frozen=True)
class ProviderExecutionResult:
    ok: bool
    provider_id: str
    model: str = ""
    response: str = ""
    diagnostics: str = ""
    exit_code: int | None = None
    duration_ms: int = 0
    error: str = ""
    cancelled: bool = False
    timed_out: bool = False


class ProviderAdapter(Protocol):
    provider_id: str

    def capabilities(self) -> set[str]: ...

    def execute(
        self,
        request: ProviderExecutionRequest,
        on_status: Callable[[str], None] | None = None,
    ) -> ProviderExecutionResult: ...

    def cancel(self) -> None: ...


class ClientProviderAdapter:
    """Adapter for existing CLI clients without leaking their result type into V2."""

    def __init__(self, client, provider_id: str, model: str = "") -> None:
        self.client = client
        self.provider_id = provider_id
        self.model = model

    def capabilities(self) -> set[str]:
        return {"CHAT", "FILES", "CREATE_TEXT_FILE", "WRITE_WORKSPACE"}

    def execute(self, request: ProviderExecutionRequest, on_status=None) -> ProviderExecutionResult:
        request.physical_workspace.mkdir(parents=True, exist_ok=True)
        self.client.workspace = request.physical_workspace
        prompt = (
            "Выполни только одну bounded-задачу в текущей рабочей папке. "
            f"Создай файл {request.filename} и запиши в него точно одну строку: {request.content}. "
            "Не создавай другие файлы, не меняй существующие и после записи проверь содержимое. "
            "Ответь кратко: имя файла и результат проверки."
        )
        result = self.client.generate(
            prompt,
            allow_full_access=True,
            on_status=on_status,
        )
        return ProviderExecutionResult(
            ok=bool(getattr(result, "ok", False)),
            provider_id=self.provider_id,
            model=self.model,
            response=str(getattr(result, "content", "") or ""),
            diagnostics=str(getattr(result, "error", "") or ""),
            exit_code=getattr(result, "returncode", None),
            duration_ms=int(float(getattr(result, "duration_seconds", 0.0) or 0.0) * 1000),
            error=str(getattr(result, "error", "") or ""),
            cancelled=bool(getattr(result, "cancelled", False)),
            timed_out=bool(getattr(result, "timed_out", False)),
        )

    def cancel(self) -> None:
        cancel = getattr(self.client, "cancel", None)
        if callable(cancel):
            cancel()


class LocalTextFileProviderAdapter:
    """Deterministic provider for a runnable Runtime V2 smoke build."""

    provider_id = "LOCAL_TEST_PROVIDER"

    def __init__(self, *, fail: bool = False, cancel: bool = False) -> None:
        self.fail = fail
        self.cancel_requested = cancel

    def capabilities(self) -> set[str]:
        return {"CHAT", "FILES", "CREATE_TEXT_FILE", "WRITE_WORKSPACE"}

    def execute(self, request: ProviderExecutionRequest, on_status=None) -> ProviderExecutionResult:
        if on_status is not None:
            on_status("создаю тестовый файл")
        if self.cancel_requested:
            return ProviderExecutionResult(False, self.provider_id, cancelled=True, diagnostics="cancelled before write")
        if self.fail:
            return ProviderExecutionResult(False, self.provider_id, error="simulated provider failure")
        request.physical_workspace.mkdir(parents=True, exist_ok=True)
        (request.physical_workspace / request.filename).write_text(request.content, encoding="utf-8")
        return ProviderExecutionResult(
            True,
            self.provider_id,
            model="local-runtime-v2-test",
            response=f"{request.filename}: verified",
            diagnostics="local deterministic execution",
            exit_code=0,
        )

    def cancel(self) -> None:
        self.cancel_requested = True
