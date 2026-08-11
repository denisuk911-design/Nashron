from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from .agent_directory import ChatAgent, mention_tokens


class ParticipationMode(StrEnum):
    DIRECT = "DIRECT"
    MULTI_DIRECT = "MULTI_DIRECT"
    TEAM_CALL = "TEAM_CALL"
    # Backward-compatible source name used by the first routing implementation.
    TEAM_DISCUSSION = "TEAM_CALL"
    REVIEW_REQUEST = "REVIEW_REQUEST"
    GENERAL_TEAM_PING = "GENERAL_TEAM_PING"
    INFO_ONLY = "INFO_ONLY"
    # Backward-compatible source name for informational broadcasts.
    BROADCAST = "INFO_ONLY"
    MANAGEMENT_COMMAND = "MANAGEMENT_COMMAND"
    CONTINUATION = "CONTINUATION"
    WORKFLOW_HANDOFF = "WORKFLOW_HANDOFF"


class RoutingDecisionType(StrEnum):
    RESPOND = "RESPOND"
    OBSERVE = "OBSERVE"
    WAIT = "WAIT"
    ESCALATE = "ESCALATE"
    IGNORE_AS_NOT_ADDRESSED = "IGNORE_AS_NOT_ADDRESSED"


@dataclass(frozen=True)
class TeamRoutingDecision:
    participation_mode: ParticipationMode
    selected: list[str]
    explicit_recipients: list[str] = field(default_factory=list)
    inferred_recipients: list[str] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)
    reason: str = ""
    router_version: str = "team-router-v1"


@dataclass(frozen=True)
class ManualRouting:
    recipient_key: str | None = None
    only_selected: bool = False
    team_discussion: bool = False
    review_request: bool = False
    no_response: bool = False


class TeamRouter:
    TEAM_TOKENS = ("команда", "отдел", "сотрудники", "все", "всем")
    GENERAL_PING_TOKENS = (
        "все тут",
        "есть кто",
        "есть кто живой",
        "кто живой",
        "кто на месте",
        "на месте",
        "на связи",
        "остальные",
        "куку",
        "ку-ку",
    )
    DISCUSSION_TOKENS = ("обсудите", "обсуждаем", "что думаете", "говорите между собой", "совещайтесь")
    REVIEW_TOKENS = ("проверь", "проверить", "ревью", "аудит", "отк", "оценить")
    MANAGEMENT_TOKENS = (
        "добавь сотрудника",
        "создай сотрудника",
        "удали сотрудника",
        "редактируй сотрудника",
        "назначь роль",
        "выдай права",
        "убери права",
        "приостанови",
        "архивируй",
        "обучи",
        "назначь навык",
    )
    BROADCAST_PREFIXES = (
        "для сведения",
        "информация:",
        "запомните",
        "новый стандарт",
        "сообщаю",
        "к сведению",
    )
    ACK_TOKENS = ("ответьте", "подтвердите", "скажите", "что думаете", "проверьте", "сделайте")
    DESTRUCTIVE_TOKENS = ("удали", "сотри", "перезапиши", "очисти", "remove", "delete", "rm -rf")
    ROLE_HINTS = {
        "QA_ENGINEER": ("проверь", "ревью", "аудит", "ошибка", "риск", "отк", "контроль"),
        "VERIFICATION_ENGINEER": ("воспроизведи", "проверка", "тест", "валид", "подтверди"),
        "DOCUMENT_CONTROL_OFFICER": ("документ", "документац", "гост", "отчет", "регламент", "инструкция"),
        "DESIGN_ENGINEER": ("pcb", "kicad", "схем", "плата", "трасс", "bom", "проектир"),
        "PROJECT_MANAGER": ("план", "срок", "задач", "приоритет", "координац"),
        "RESEARCH_ASSISTANT": ("найди источник", "даташит", "datasheet", "поиск", "исслед"),
    }

    def __init__(self, general_chat_response: str = "SINGLE") -> None:
        policy = str(general_chat_response or "SINGLE").upper()
        self.general_chat_response = policy if policy in {"SINGLE", "SMALL_GROUP", "ALL"} else "SINGLE"

    def decide(
        self,
        text: str,
        agents: list[ChatAgent],
        *,
        active_owner: list[str] | None = None,
        manual: ManualRouting | None = None,
        eligible_keys: set[str] | None = None,
        blocked_agents: list[ChatAgent] | None = None,
        recently_answered: set[str] | None = None,
    ) -> TeamRoutingDecision:
        manual = manual or ManualRouting()
        active_agents = list(agents)
        active_keys = {agent.key for agent in active_agents}
        eligible = active_keys if eligible_keys is None else active_keys & set(eligible_keys)
        recently_answered = set(recently_answered or ())
        blocked_mentions = self._mentioned_agents(text, blocked_agents or [])
        if not active_agents:
            return TeamRoutingDecision(ParticipationMode.DIRECT, [], reason="no_active_roster")

        if manual.no_response:
            return self._decision(ParticipationMode.BROADCAST, [], active_agents, reason="manual_no_response")

        if manual.recipient_key and manual.recipient_key in active_keys:
            mode = ParticipationMode.TEAM_DISCUSSION if manual.team_discussion else ParticipationMode.DIRECT
            selected = [manual.recipient_key] if manual.recipient_key in eligible else []
            return self._decision(mode, selected, active_agents, explicit=selected, reason="manual_recipient")

        mentions = self._mentioned_agents(text, active_agents)
        if blocked_mentions and not mentions:
            return self._decision(
                ParticipationMode.DIRECT,
                [],
                active_agents,
                explicit=blocked_mentions,
                reason="addressed_employee_inactive_or_chat_denied",
            )
        if manual.only_selected and manual.recipient_key:
            return self._decision(ParticipationMode.DIRECT, [], active_agents, reason="manual_recipient_not_available")

        if manual.team_discussion:
            selected = [key for key in (mentions or [agent.key for agent in active_agents]) if key in eligible]
            return self._decision(ParticipationMode.TEAM_CALL, selected, active_agents, explicit=mentions, reason="manual_team_discussion")

        if manual.review_request:
            selected = [key for key in (mentions or self._reviewers(active_agents, limit=1)) if key in eligible]
            return self._decision(ParticipationMode.REVIEW_REQUEST, selected, active_agents, explicit=mentions, reason="manual_review_request")

        if mentions:
            mode = ParticipationMode.REVIEW_REQUEST if self._looks_like_review_request(text, mentions, active_agents) else ParticipationMode.DIRECT
            selected = mentions[:2] if self._looks_like_team_discussion(text) and len(mentions) > 1 else mentions[:1] if len(mentions) == 1 else mentions
            selected = [key for key in selected if key in eligible]
            if len(selected) > 1:
                mode = ParticipationMode.TEAM_CALL if self._looks_like_team_discussion(text) else ParticipationMode.MULTI_DIRECT
            return self._decision(mode, selected, active_agents, explicit=selected, reason="explicit_name_or_alias")

        if active_owner and self._looks_like_continuation(text) and not self._looks_like_general_team_ping(text):
            selected = [key for key in active_owner if key in eligible][:1]
            if selected:
                return self._decision(ParticipationMode.CONTINUATION, selected, active_agents, inferred=selected, reason="active_thread_owner")

        lowered = self._norm(text)
        if any(token in lowered for token in self.MANAGEMENT_TOKENS):
            selected = [key for key in self._role_relevant_subset(text, active_agents, limit=1) if key in eligible]
            return self._decision(ParticipationMode.MANAGEMENT_COMMAND, selected, active_agents, inferred=selected, reason="management_command")

        if self._looks_like_broadcast(text):
            return self._decision(ParticipationMode.INFO_ONLY, [], active_agents, reason="informational_broadcast")

        if self._looks_like_general_team_ping(text):
            selected = [
                agent.key
                for agent in active_agents
                if agent.key in eligible and (not self._looks_like_remaining_ping(text) or agent.key not in recently_answered)
            ]
            reason = "remaining_team_ping" if self._looks_like_remaining_ping(text) else "general_team_ping"
            return self._decision(ParticipationMode.GENERAL_TEAM_PING, selected, active_agents, reason=reason)

        if self._looks_like_team_discussion(text):
            selected = [agent.key for agent in active_agents if agent.key in eligible]
            return self._decision(ParticipationMode.TEAM_CALL, selected, active_agents, inferred=selected, reason="team_call_request")

        selected = [key for key in self._role_relevant_subset(text, active_agents, limit=1) if key in eligible]
        if selected:
            return self._decision(ParticipationMode.DIRECT, selected, active_agents, inferred=selected, reason="role_relevant_default")
        fallback = [key for key in (active_owner or []) if key in eligible]
        if not fallback:
            fallback = [agent.key for agent in active_agents if agent.key in eligible]
        if fallback:
            if self.general_chat_response == "ALL":
                chosen = fallback
            elif self.general_chat_response == "SMALL_GROUP":
                chosen = fallback[:3]
            else:
                chosen = fallback[:1]
            return self._decision(
                ParticipationMode.DIRECT,
                chosen,
                active_agents,
                inferred=chosen,
                reason="default_conversational_owner",
            )
        return self._decision(
            ParticipationMode.DIRECT,
            [],
            active_agents,
            reason="no_explicit_recipient_or_relevant_role",
        )

    def _mentioned_agents(self, text: str, agents: list[ChatAgent]) -> list[str]:
        lowered = self._norm(text)
        matches_by_token: dict[str, list[str]] = {}
        for agent in agents:
            for token in sorted(mention_tokens(agent), key=len, reverse=True):
                if token and self._contains_token(lowered, token):
                    matches_by_token.setdefault(token, []).append(agent.key)
                    break
        ambiguous = {token for token, keys in matches_by_token.items() if len(set(keys)) > 1}
        found = [key for token, keys in matches_by_token.items() if token not in ambiguous for key in keys]
        return self._dedupe(found)

    def _role_relevant_subset(self, text: str, agents: list[ChatAgent], limit: int) -> list[str]:
        lowered = self._norm(text)
        scored: list[tuple[int, int, str]] = []
        for index, agent in enumerate(agents):
            score = 0
            for role in agent.roles:
                score += sum(1 for token in self.ROLE_HINTS.get(role, ()) if token in lowered)
            scored.append((-score, index, agent.key))
        scored.sort()
        selected = [key for score, _index, key in scored if score < 0][:limit]
        return selected

    def _reviewers(self, agents: list[ChatAgent], limit: int) -> list[str]:
        reviewers = [agent.key for agent in agents if "QA_ENGINEER" in agent.roles or "VERIFICATION_ENGINEER" in agent.roles]
        return reviewers[:limit]

    def _looks_like_review_request(self, text: str, mentions: list[str], agents: list[ChatAgent]) -> bool:
        lowered = self._norm(text)
        if not any(token in lowered for token in self.REVIEW_TOKENS):
            return False
        mentioned_roles = [agent.roles for agent in agents if agent.key in mentions]
        return any("QA_ENGINEER" in roles or "VERIFICATION_ENGINEER" in roles for roles in mentioned_roles)

    def _looks_like_team_discussion(self, text: str) -> bool:
        lowered = self._norm(text)
        return any(self._contains_token(lowered, token) for token in self.TEAM_TOKENS) or any(
            token in lowered for token in self.DISCUSSION_TOKENS
        )

    def _looks_like_general_team_ping(self, text: str) -> bool:
        lowered = self._norm(text).rstrip("?!.,")
        return any(self._contains_token(lowered, token) for token in self.GENERAL_PING_TOKENS)

    def _looks_like_remaining_ping(self, text: str) -> bool:
        lowered = self._norm(text).rstrip("?!.,")
        return lowered.startswith("остальные")

    def _looks_like_broadcast(self, text: str) -> bool:
        lowered = self._norm(text).strip()
        if "?" in text or any(token in lowered for token in self.ACK_TOKENS):
            return False
        return any(lowered.startswith(prefix) for prefix in self.BROADCAST_PREFIXES)

    def _looks_like_continuation(self, text: str) -> bool:
        lowered = self._norm(text)
        if len(lowered) > 80:
            return False
        tokens = (
            "а ограничения",
            "что скажешь",
            "еще раз",
            "ещё раз",
            "попробуй",
            "продолжай",
            "дальше",
            "проверь еще",
            "проверь ещё",
            "так и сделай",
        )
        return any(token in lowered for token in tokens) or lowered.endswith("?")

    def _decision(
        self,
        mode: ParticipationMode,
        selected: list[str],
        agents: list[ChatAgent],
        *,
        explicit: list[str] | None = None,
        inferred: list[str] | None = None,
        reason: str,
    ) -> TeamRoutingDecision:
        selected = self._dedupe([key for key in selected if key])
        selected_set = set(selected)
        excluded = {
            agent.key: ("selected_other_employee" if selected else "not_addressed")
            for agent in agents
            if agent.key not in selected_set
        }
        return TeamRoutingDecision(
            participation_mode=mode,
            selected=selected,
            explicit_recipients=self._dedupe(explicit or []),
            inferred_recipients=self._dedupe(inferred or []),
            excluded=excluded,
            reason=reason,
        )

    @staticmethod
    def _contains_token(text: str, token: str) -> bool:
        token = re.escape(token.lower().replace("ё", "е"))
        return re.search(rf"(^|[^a-zа-я0-9_@])@?{token}([^a-zа-я0-9_]|$)", text) is not None

    @staticmethod
    def _norm(text: str) -> str:
        return " ".join(text.lower().replace("ё", "е").split())

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        result: list[str] = []
        for item in items:
            if item not in result:
                result.append(item)
        return result
