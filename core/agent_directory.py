from __future__ import annotations

from dataclasses import dataclass
import json
import re

from .database import Database
from .communication_style_service import CommunicationStyle
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
    "CUSTOM_ENGAGEMENT_LEAD": "руководитель взаимодействия с клиентом",
    "CUSTOM_DOMAIN_SPECIALIST": "профильный специалист",
    "CUSTOM_ANALYST": "аналитик",
    "CUSTOM_REVIEWER": "рецензент",
    "CUSTOM_TECHNICAL_REVIEWER": "технический рецензент",
    "CUSTOM_CRITICAL_REVIEWER": "критический рецензент",
    "CUSTOM_DEVELOPER": "разработчик",
    "CUSTOM_SOFTWARE_ENGINEER": "инженер-программист",
    "CUSTOM_ARCHITECT": "архитектор",
    "CUSTOM_QA": "специалист по качеству",
    "CUSTOM_DESIGNER": "дизайнер",
    "CUSTOM_PRODUCT_LEAD": "руководитель продукта",
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
    full_name: str = ""
    preferred_name: str = ""
    informal_name: str = ""
    communication_profile: dict[str, object] | None = None

    @property
    def primary_role(self) -> str:
        return self.roles[0] if self.roles else "CUSTOM_ROLE"

    @property
    def engine_name(self) -> str:
        return ENGINE_BY_PROVIDER.get(self.provider_id, self.provider_id)

    @property
    def chat_display_name(self) -> str:
        """Return the short human-facing name used in the chat chrome."""
        return chat_display_name(
            display_name=self.display_name,
            full_name=self.full_name,
            preferred_name=self.preferred_name,
            primary_role=self.primary_role,
        )


_ROLEISH_NAME_PARTS = {
    "admin", "administrator", "analyst", "assistant", "developer", "designer",
    "employee", "engineer", "manager", "owner", "qa", "reviewer", "specialist",
    "сотрудник", "инженер", "менеджер", "разработчик", "руководитель", "специалист",
}


def _is_roleish_name(value: str, primary_role: str) -> bool:
    compact = "_".join(value.lower().split())
    if not compact:
        return True
    if compact == primary_role.lower() or compact in ROLE_NAMES:
        return True
    if "_" in compact and compact.upper() == compact:
        return True
    words = set(re.findall(r"[a-zа-яё]+", compact, flags=re.IGNORECASE))
    return bool(words) and words.issubset(_ROLEISH_NAME_PARTS)


def chat_display_name(
    *,
    display_name: str,
    full_name: str = "",
    preferred_name: str = "",
    primary_role: str = "CUSTOM_ROLE",
) -> str:
    """Choose a natural chat name and never expose a role placeholder as a name."""
    candidates = (preferred_name.strip(), display_name.strip(), full_name.strip())
    for candidate in candidates:
        if not _is_roleish_name(candidate, primary_role):
            return candidate.split()[0]
    return "Сотрудник"


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
        try:
            raw_communication = json.loads(str(row["communication_profile"] or "{}"))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raw_communication = {}
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
                full_name=str(row["full_name"] or row["display_name"]) if "full_name" in row.keys() else str(row["display_name"]),
                preferred_name=str(row["preferred_name"] or "") if "preferred_name" in row.keys() else "",
                informal_name=str(row["informal_name"] or "") if "informal_name" in row.keys() else "",
                communication_profile=raw_communication if isinstance(raw_communication, dict) else {},
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
    communication = CommunicationStyle.from_profile(agent.communication_profile)
    chat_name = agent.chat_display_name
    address_name = agent.preferred_name.strip() or chat_name
    nickname_note = (
        f"Близкие коллеги иногда используют короткое имя {agent.informal_name.strip()}. "
        if agent.informal_name.strip() and agent.informal_name.strip() != address_name
        else ""
    )
    style = (
        f"В общении тебя обычно зовут {address_name}. "
        f"{nickname_note}"
        f"Профиль общения: прямота {communication.directness}/5, доброжелательность {communication.warmth}/5, "
        f"формальность {communication.formality}/5, юмор {communication.humor}/5, подробность {communication.verbosity}/5, "
        f"эмоциональность {communication.emotionality}/5, объяснения {communication.explanation_style}. "
        "Соблюдай эти параметры естественно, без перечисления их собеседнику. "
    )
    voice = (
        f"Твоё полное имя: {agent.full_name or chat_name}. В чате ты отображаешься как {chat_name}. "
        f"Ты работаешь как {role_name} через {agent.engine_name}. "
        f"{style}"
        "Отвечай от первого лица, коротко, предметно и профессионально. "
        "Не изображай других сотрудников и не пиши диалог с их именами внутри своего ответа. "
        "Если задача относится к твоей роли, бери свою часть. Если видишь риск, ошибку или слабый план, укажи конкретно. "
        "В социальном разговоре веди себя как человек с собственной манерой общения: профессия не должна становиться темой без рабочего запроса. "
        "Если данных мало, попроси недостающий минимум, без занудства и давления на пользователя."
        f"{description}"
    )
    return AgentSpec(
        key=agent.key,
        display_name=chat_name,
        engine_name=agent.engine_name,
        voice=voice,
    )


def mention_tokens(agent: ChatAgent) -> set[str]:
    tokens = {agent.key.lower(), agent.agent_id.lower()}
    for part in {agent.display_name, agent.chat_display_name, agent.full_name, agent.preferred_name, agent.informal_name}:
        for part in part.lower().replace("ё", "е").split():
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
    first_name = agent.chat_display_name.lower().replace("ё", "е").split()[0] if agent.chat_display_name.split() else ""
    if len(first_name) >= 5 and re.fullmatch(r"[а-я]+", first_name):
        tokens.add(first_name[:4])
    if len(first_name) >= 6 and re.fullmatch(r"[а-я]+", first_name):
        tokens.add(first_name[:3])
    return tokens
