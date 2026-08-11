from __future__ import annotations

from dataclasses import dataclass
import json
import re

from .database import Database
from .models import AgentSpec
from .tool_access import effective_permissions_for_agent


ENGINE_BY_PROVIDER = {
    "CODEX_CLI": "Codex CLI",
    "GEMINI_CLI": "Gemini CLI",
    "CLAUDE_CLI": "Claude CLI",
    "FUTURE_PROVIDER": "не настроенный провайдер",
    "UNAVAILABLE": "не настроенный провайдер",
}

ROLE_NAMES = {
    "PROJECT_MANAGER": "руководитель проекта",
    "DESIGN_ENGINEER": "инженер-проектировщик PCB/KiCad",
    "QA_ENGINEER": "инженер ОТК и технического ревью",
    "VERIFICATION_ENGINEER": "инженер проверки и воспроизводимости",
    "DOCUMENT_CONTROL_OFFICER": "специалист по документации",
    "LEARNING_COORDINATOR": "координатор обучения и развития навыков",
    "RESEARCH_ASSISTANT": "исследователь источников и даташитов",
    "CUSTOM_ROLE": "сотрудник с пользовательской ролью",
}


@dataclass(frozen=True)
class ChatAgent:
    key: str
    agent_id: str
    display_name: str
    provider_id: str
    roles: list[str]
    persona_id: str | None
    description: str
    avatar_path: str | None
    lifecycle_state: str = "ACTIVE"
    aliases: tuple[str, ...] = ()

    @property
    def primary_role(self) -> str:
        return self.roles[0] if self.roles else "CUSTOM_ROLE"

    @property
    def engine_name(self) -> str:
        return ENGINE_BY_PROVIDER.get(self.provider_id, self.provider_id)


def agent_key_from_id(agent_id: str) -> str:
    return agent_id[6:] if agent_id.startswith("agent-") else agent_id


def agent_id_from_key(agent_key: str) -> str:
    return agent_key if agent_key.startswith("agent-") else f"agent-{agent_key}"


def list_chat_agents(
    database: Database,
    active_only: bool = True,
    include_without_chat: bool = False,
    organization_id: str | None = None,
) -> list[ChatAgent]:
    agents: list[ChatAgent] = []
    organization_agent_ids = database.list_organization_agent_ids(organization_id) if organization_id else None
    for row in database.list_agent_profiles():
        if active_only and str(row["lifecycle_state"]) != "ACTIVE":
            continue
        agent_id = str(row["agent_id"])
        if organization_agent_ids is not None and agent_id not in organization_agent_ids:
            continue
        roles = database.list_agent_roles(agent_id)
        if not include_without_chat and "CHAT" not in effective_permissions_for_agent(database, agent_id):
            continue
        try:
            raw_aliases = json.loads(str(row["aliases"] or "[]"))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raw_aliases = []
        aliases = tuple(str(alias).strip() for alias in raw_aliases if str(alias).strip()) if isinstance(raw_aliases, list) else ()
        agents.append(
            ChatAgent(
                key=agent_key_from_id(agent_id),
                agent_id=agent_id,
                display_name=str(row["display_name"]),
                provider_id=str(row["provider_id"]),
                roles=roles,
                persona_id=str(row["persona_id"]) if row["persona_id"] else None,
                description=str(row["description"] or ""),
                avatar_path=str(row["avatar_path"]) if row["avatar_path"] else None,
                lifecycle_state=str(row["lifecycle_state"]),
                aliases=aliases,
            )
        )
    return agents


def get_chat_agent(database: Database, agent_key: str) -> ChatAgent | None:
    wanted_id = agent_id_from_key(agent_key)
    for agent in list_chat_agents(database, active_only=False):
        if agent.agent_id == wanted_id or agent.key == agent_key:
            return agent
    return None


def agent_spec_from_profile(agent: ChatAgent) -> AgentSpec:
    role_name = ROLE_NAMES.get(agent.primary_role, agent.primary_role.replace("_", " ").lower())
    description = f" Описание профиля: {agent.description.strip()}" if agent.description.strip() else ""
    voice = (
        f"Ты {agent.display_name}. Ты работаешь как {role_name} через {agent.engine_name}. "
        "Отвечай от первого лица, коротко, предметно и профессионально. "
        "Не изображай других сотрудников и не пиши диалог с их именами внутри своего ответа. "
        "Если задача относится к твоей роли, бери свою часть. Если видишь риск, ошибку или слабый план, укажи конкретно. "
        "Если данных мало, попроси недостающий минимум, без занудства и давления на пользователя."
        f"{description}"
    )
    return AgentSpec(
        key=agent.key,
        display_name=agent.display_name,
        engine_name=agent.engine_name,
        voice=voice,
    )


def mention_tokens(agent: ChatAgent) -> set[str]:
    tokens = {agent.key.lower(), agent.agent_id.lower()}
    if agent.key == "roman":
        tokens.update({"роман", "романа", "роману", "романе", "романом"})
    if agent.key == "petr":
        tokens.update({"петр", "пётр", "петра", "петру", "петре", "петром"})
    for part in agent.display_name.lower().replace("ё", "е").split():
        if len(part) >= 2:
            tokens.add(part)
        if len(part) >= 4 and re.search(r"[а-я]", part):
            stem = part.rstrip("аеёиоуыэюяйь")
            if len(stem) >= 4:
                tokens.add(stem)
                if len(stem) >= 5 and stem[-1] == stem[-2]:
                    tokens.add(stem[:-1])
                for suffix in ("а", "у", "е", "ы", "ой", "ою", "ом"):
                    tokens.add(f"{stem}{suffix}")
    if agent.persona_id:
        tokens.add(agent.persona_id.lower())
    for alias in agent.aliases:
        normalized = " ".join(str(alias).lower().replace("ё", "е").split())
        if normalized:
            tokens.add(normalized)
    # Safe normalized-name form: the short prefix still uses token boundaries
    # and must resolve to an unambiguous employee in the current roster.
    first_name = agent.display_name.lower().replace("ё", "е").split()[0] if agent.display_name.split() else ""
    if len(first_name) >= 5 and re.fullmatch(r"[а-я]+", first_name):
        tokens.add(first_name[:4])
    if len(first_name) >= 6 and re.fullmatch(r"[а-я]+", first_name):
        tokens.add(first_name[:3])
    return tokens
