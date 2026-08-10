from __future__ import annotations

from dataclasses import dataclass

from .context_snapshot_service import ContextSnapshotService
from .prompt_builder import PromptBuilder


@dataclass(frozen=True)
class ContextPackage:
    role: str
    task_id: str | None
    prompt: str
    immediate_context: tuple[str, ...] = ()
    task_context: tuple[str, ...] = ()
    organization_context: tuple[str, ...] = ()
    conversation_context: tuple[str, ...] = ()


class ContextAssembler:
    """Role-aware boundary around PromptBuilder.

    Phase 1 preserves the existing prompt content and creates a separate place
    for future standards, knowledge and reference-design retrieval.
    """

    def __init__(self, prompt_builder: PromptBuilder) -> None:
        self.prompt_builder = prompt_builder

    def assemble(
        self,
        *,
        role: str,
        task_id: str | None,
        conversation_id: int,
        user_message: str,
        allow_local_tools: bool,
        agent_key: str,
        peer_context: str,
        autonomous_goal: str,
        autonomous_turn: int,
        complete_on_goal: bool,
        participation_mode: str = "DIRECT",
        thread_context_lines: list[str] | None = None,
    ) -> ContextPackage:
        owner_keys = self.prompt_builder._thread_owner_keys(thread_context_lines or [])
        snapshot = ContextSnapshotService(self.prompt_builder.database).build(
            conversation_id=conversation_id,
            user_message=user_message,
            agent_key=agent_key,
            thread_owner_keys=owner_keys,
        )
        task_context: list[str] = []
        if task_id:
            task = self.prompt_builder.database.get_task(task_id)
            if task is not None:
                task_context.append(f"task_id={task_id}; state={task['state']}; title={task['title']}")
                task_context.extend(
                    f"transition={row['previous_state']}->{row['next_state']}; reason={row['reason']}"
                    for row in self.prompt_builder.database.list_task_transitions(task_id)[-5:]
                )
        conversation_context = [f"participation_mode={participation_mode}", *(thread_context_lines or [])]
        prompt = self.prompt_builder.build(
            conversation_id,
            user_message,
            allow_local_tools=allow_local_tools,
            agent_key=agent_key,
            peer_context=peer_context,
            autonomous_goal=autonomous_goal,
            autonomous_turn=autonomous_turn,
            complete_on_goal=complete_on_goal,
            task_id=task_id,
            participation_mode=participation_mode,
            thread_context_lines=thread_context_lines,
        )
        return ContextPackage(
            role=role,
            task_id=task_id,
            prompt=prompt,
            immediate_context=tuple(snapshot.immediate_lines),
            task_context=tuple(task_context),
            organization_context=(f"agent_key={agent_key}", f"role={role}"),
            conversation_context=tuple(conversation_context),
        )
