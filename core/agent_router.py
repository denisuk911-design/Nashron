from __future__ import annotations

from dataclasses import dataclass

from .agent_directory import get_chat_agent
from .database import Database


@dataclass(frozen=True)
class AgentRoute:
    agent_key: str
    agent_id: str
    role: str
    provider: str


class AgentRouter:
    def __init__(self, database: Database | None = None) -> None:
        self.database = database

    def route(self, agent_key: str) -> AgentRoute:
        if self.database is not None:
            agent = get_chat_agent(self.database, agent_key)
            if agent is not None:
                return AgentRoute(
                    agent_key=agent.key,
                    agent_id=agent.agent_id,
                    role=agent.primary_role,
                    provider=agent.provider_id,
                )
        return AgentRoute(
            agent_key=agent_key,
            agent_id=f"agent-{agent_key}",
            role="ASSISTANT",
            provider="UNKNOWN",
        )

    def role_for_agent(self, agent_key: str) -> str:
        return self.route(agent_key).role
