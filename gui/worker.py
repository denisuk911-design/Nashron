from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from core.models import CodexResult
from core.prompt_builder import PromptBuilder
from core.run_status import RunStatus, status_label


class GenerateWorker(QThread):
    delta_received = Signal(str)
    status_received = Signal(str)
    run_status_received = Signal(str)
    finished_with_result = Signal(object)

    def __init__(
        self,
        prompt_builder: PromptBuilder,
        generation_client,
        conversation_id: int,
        user_message: str,
        allow_local_tools: bool = False,
        agent_key: str = "roman",
        peer_context: str = "",
        autonomous_goal: str = "",
        autonomous_turn: int = 0,
        complete_on_goal: bool = False,
        run_id: str | None = None,
        task_id: str | None = None,
        participation_mode: str = "DIRECT",
        thread_context_lines: list[str] | None = None,
        active_work_context_lines: list[str] | None = None,
        execution_contract_lines: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.prompt_builder = prompt_builder
        self.generation_client = generation_client
        self.conversation_id = conversation_id
        self.user_message = user_message
        self.allow_local_tools = allow_local_tools
        self.agent_key = agent_key
        self.peer_context = peer_context
        self.autonomous_goal = autonomous_goal
        self.autonomous_turn = autonomous_turn
        self.complete_on_goal = complete_on_goal
        self.run_id = run_id
        self.task_id = task_id
        self.participation_mode = participation_mode
        self.thread_context_lines = thread_context_lines or []
        self.active_work_context_lines = active_work_context_lines or []
        self.execution_contract_lines = execution_contract_lines or []

    def run(self) -> None:
        try:
            self._set_status(RunStatus.PREPARING_CONTEXT)
            prompt = self.prompt_builder.build(
                self.conversation_id,
                self.user_message,
                allow_local_tools=self.allow_local_tools,
                agent_key=self.agent_key,
                peer_context=self.peer_context,
                autonomous_goal=self.autonomous_goal,
                autonomous_turn=self.autonomous_turn,
                complete_on_goal=self.complete_on_goal,
                task_id=self.task_id,
                run_id=self.run_id,
                participation_mode=self.participation_mode,
                thread_context_lines=self.thread_context_lines,
                active_work_context_lines=self.active_work_context_lines,
                execution_contract_lines=self.execution_contract_lines,
            )
            self._set_status(RunStatus.STARTING_PROVIDER)
            self._set_status(RunStatus.WAITING_FOR_PROVIDER)
            result = self.generation_client.generate(
                prompt,
                allow_full_access=self.allow_local_tools,
                on_delta=self.delta_received.emit,
                on_status=self._provider_status,
            )
            if result.ok:
                self._set_status(RunStatus.PREPARING_RESPONSE)
            elif result.timed_out:
                self._set_status(RunStatus.TIMED_OUT)
            elif result.cancelled:
                self._set_status(RunStatus.CANCELLED)
            else:
                self._set_status(RunStatus.FAILED)
        except Exception as exc:  # GUI boundary: report instead of crashing Qt thread.
            result = CodexResult(False, "", None, 0.0, str(exc))
            self._set_status(RunStatus.FAILED)
        self.finished_with_result.emit(result)

    def _set_status(self, status: RunStatus) -> None:
        self.run_status_received.emit(status.value)
        self.status_received.emit(status_label(status))

    def _provider_status(self, status: str) -> None:
        clean = str(status or "").strip()
        if not clean:
            return
        lowered = clean.lower()
        if any(token in lowered for token in ("чита", "read", "файл")):
            self.run_status_received.emit(RunStatus.READING_FILES.value)
        else:
            self.run_status_received.emit(RunStatus.RUNNING_TOOLS.value)
        self.status_received.emit(clean)

    def cancel(self) -> None:
        self.generation_client.cancel()
