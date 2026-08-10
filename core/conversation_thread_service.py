from __future__ import annotations

from dataclasses import dataclass

from .agent_directory import agent_id_from_key, agent_key_from_id
from .database import Database
from .team_routing import ParticipationMode, TeamRoutingDecision


@dataclass(frozen=True)
class ConversationThreadSnapshot:
    thread_id: str
    active_addressee_agent_id: str | None
    active_task_id: str | None
    active_topic: str | None
    last_user_message_id: int | None
    expected_next_actor: str | None
    thread_status: str

    @property
    def owner_keys(self) -> list[str]:
        if self.active_addressee_agent_id:
            return [agent_key_from_id(self.active_addressee_agent_id)]
        if self.expected_next_actor:
            return [item.strip() for item in self.expected_next_actor.split(",") if item.strip()]
        return []


class ConversationThreadService:
    """Persists the active chat owner so short follow-ups survive restarts."""

    def __init__(self, database: Database, conversation_id: int) -> None:
        self.database = database
        self.conversation_id = conversation_id
        self.thread_id = f"conversation-{conversation_id}"

    def snapshot(self) -> ConversationThreadSnapshot:
        row = self.database.get_conversation_thread(self.thread_id)
        if row is None:
            row = self.database.get_active_conversation_thread(self.conversation_id)
        if row is None:
            return ConversationThreadSnapshot(
                thread_id=self.thread_id,
                active_addressee_agent_id=None,
                active_task_id=None,
                active_topic=None,
                last_user_message_id=None,
                expected_next_actor=None,
                thread_status="OPEN",
            )
        return ConversationThreadSnapshot(
            thread_id=str(row["id"]),
            active_addressee_agent_id=str(row["active_addressee_agent_id"]) if row["active_addressee_agent_id"] else None,
            active_task_id=str(row["active_task_id"]) if row["active_task_id"] else None,
            active_topic=str(row["active_topic"]) if row["active_topic"] else None,
            last_user_message_id=int(row["last_user_message_id"]) if row["last_user_message_id"] is not None else None,
            expected_next_actor=str(row["expected_next_actor"]) if row["expected_next_actor"] else None,
            thread_status=str(row["thread_status"]),
        )

    def owner_keys(self) -> list[str]:
        return self.snapshot().owner_keys

    def apply_routing_decision(
        self,
        decision: TeamRoutingDecision,
        *,
        message_id: int | None,
        task_id: str | None,
        topic: str,
    ) -> ConversationThreadSnapshot:
        previous = self.snapshot()
        active_addressee_agent_id = previous.active_addressee_agent_id
        expected_next_actor = previous.expected_next_actor
        active_topic = topic.strip()[:240] if topic.strip() else previous.active_topic

        mode = ParticipationMode(str(decision.participation_mode))
        if decision.selected:
            if mode in {ParticipationMode.DIRECT, ParticipationMode.CONTINUATION, ParticipationMode.REVIEW_REQUEST, ParticipationMode.MANAGEMENT_COMMAND}:
                active_addressee_agent_id = agent_id_from_key(decision.selected[0])
                expected_next_actor = decision.selected[0]
            elif mode == ParticipationMode.TEAM_DISCUSSION:
                active_addressee_agent_id = None
                expected_next_actor = ",".join(decision.selected)
        elif mode == ParticipationMode.BROADCAST:
            active_topic = previous.active_topic or active_topic
        else:
            active_addressee_agent_id = None
            expected_next_actor = None

        self.database.upsert_conversation_thread(
            thread_id=self.thread_id,
            conversation_id=self.conversation_id,
            active_addressee_agent_id=active_addressee_agent_id,
            active_task_id=task_id or previous.active_task_id,
            active_topic=active_topic,
            last_user_message_id=message_id or previous.last_user_message_id,
            expected_next_actor=expected_next_actor,
            thread_status="OPEN",
        )
        return self.snapshot()

    def prompt_lines(self) -> list[str]:
        snapshot = self.snapshot()
        return [
            f"- conversation_thread_id: {snapshot.thread_id}",
            f"- active_addressee_agent_id: {snapshot.active_addressee_agent_id or 'нет'}",
            f"- active_task_id: {snapshot.active_task_id or 'нет'}",
            f"- active_topic: {snapshot.active_topic or 'нет'}",
            f"- last_user_message_id: {snapshot.last_user_message_id if snapshot.last_user_message_id is not None else 'нет'}",
            f"- expected_next_actor: {snapshot.expected_next_actor or 'нет'}",
            f"- thread_status: {snapshot.thread_status}",
        ]
