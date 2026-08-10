from __future__ import annotations

from dataclasses import dataclass

from .prompt_builder import PromptBuilder


@dataclass(frozen=True)
class ContextPackage:
    role: str
    task_id: str | None
    prompt: str


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
    ) -> ContextPackage:
        prompt = self.prompt_builder.build(
            conversation_id,
            user_message,
            allow_local_tools=allow_local_tools,
            agent_key=agent_key,
            peer_context=peer_context,
            autonomous_goal=autonomous_goal,
            autonomous_turn=autonomous_turn,
            complete_on_goal=complete_on_goal,
        )
        return ContextPackage(role=role, task_id=task_id, prompt=prompt)
