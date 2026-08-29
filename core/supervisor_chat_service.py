from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class SupervisorChatResult:
    """Owner-safe result returned by the Supervisor chat application boundary."""

    ok: bool
    message: str
    route: str = "LOCAL"
    action: str = ""
    confirmation_required: bool = False
    confirmation_token: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class SupervisorChatApplicationService:
    """Natural-language command facade over Team2050 Application Services.

    The chat window never mutates the database or settings directly.  A caller
    supplies already-initialized services and a settings persistence callback.
    """

    _DANGEROUS = re.compile(r"\b(удал|увол|замени|переназнач|delete|remove|fire|replace)\w*", re.I)
    _COMPLEX = re.compile(
        r"\b(создай организац|создай команд|найми|увол|переназнач|роль|skill|скилл|provider|провайдер|goal|цель|replan|переплан|запусти|отмени|approve|одобр)\w*",
        re.I,
    )
    _DANGEROUS_RU = re.compile(
        r"\b(?:\u0443\u0434\u0430\u043b\w*|\u0443\u0432\u043e\u043b\w*|\u0437\u0430\u043c\u0435\u043d\w*|\u043f\u0435\u0440\u0435\u043d\u0430\u0437\u043d\u0430\u0447\w*)",
        re.I,
    )
    _COMPLEX_RU = re.compile(
        r"\b(?:\u0441\u043e\u0437\u0434\u0430\u0439|\u043d\u0430\u0439\u043c\u0438|\u0443\u0432\u043e\u043b\u044c|\u043f\u0435\u0440\u0435\u043d\u0430\u0437\u043d\u0430\u0447|\u0440\u043e\u043b\u044c|\u0441\u043a\u0438\u043b\u043b|\u043f\u0440\u043e\u0432\u0430\u0439\u0434\u0435\u0440|\u0446\u0435\u043b\u044c|\u043f\u0435\u0440\u0435\u043f\u043b\u0430\u043d|\u0437\u0430\u043f\u0443\u0441\u0442\u0438|\u043e\u0442\u043c\u0435\u043d\u0438|\u043e\u0434\u043e\u0431\u0440\u0438)",
        re.I,
    )

    def __init__(
        self,
        *,
        supervisor_service: Any,
        universal_service: Any | None = None,
        management_service: Any | None = None,
        settings: dict[str, Any] | None = None,
        save_settings: Callable[[dict[str, Any]], None] | None = None,
        local_runtime: Any | None = None,
        strong_handler: Callable[[str, str | None], str] | None = None,
    ) -> None:
        self.supervisor_service = supervisor_service
        self.universal_service = universal_service
        self.management_service = management_service
        self.settings = settings if settings is not None else {}
        self.save_settings = save_settings or (lambda _settings: None)
        self.local_runtime = local_runtime
        self.strong_handler = strong_handler
        self._pending: dict[str, tuple[str, str | None]] = {}

    def handle(self, text: str, organization_id: str | None = None, *, confirmed: bool = False) -> SupervisorChatResult:
        text = " ".join(str(text or "").split())
        if not text:
            return SupervisorChatResult(False, "Опишите действие для Supervisor.", action="empty")
        route = self._route(text)
        lowered = text.casefold()

        if (self._DANGEROUS.search(text) or self._DANGEROUS_RU.search(text)) and not confirmed:
            token = f"confirm-{len(self._pending) + 1}"
            self._pending[token] = (text, organization_id)
            return SupervisorChatResult(
                False,
                "Это действие изменит состав или назначение команды. Подтвердите выполнение.",
                route=route,
                action="confirmation",
                confirmation_required=True,
                confirmation_token=token,
            )
        if confirmed and text in {item[0] for item in self._pending.values()}:
            self._pending = {key: value for key, value in self._pending.items() if value[0] != text}

        try:
            # Known owner commands always stay inside Application Services.
            # Model routing is only for requests without a deterministic
            # command mapping.
            if any(token in lowered for token in ("\u0441\u043e\u0437\u0434\u0430\u0439 \u043e\u0440\u0433\u0430\u043d\u0438\u0437\u0430\u0446\u0438\u044e", "create organization")):
                return self._create_organization(text)
            if any(token in lowered for token in ("\u0441\u043e\u0437\u0434\u0430\u0439 \u043a\u043e\u043c\u0430\u043d\u0434\u0443", "create team")):
                return self._create_team(text, organization_id)
            if any(token in lowered for token in ("\u0443\u0434\u0430\u043b\u0438 \u0441\u043e\u0442\u0440\u0443\u0434\u043d\u0438\u043a\u0430", "\u0443\u0432\u043e\u043b\u044c", "delete employee", "fire")):
                return self._delete_employee(text)
            if any(token in lowered for token in ("\u043f\u0435\u0440\u0435\u043d\u0430\u0437\u043d\u0430\u0447", "replace employee", "\u0437\u0430\u043c\u0435\u043d\u0438 \u0441\u043e\u0442\u0440\u0443\u0434\u043d\u0438\u043a\u0430")):
                return self._reassign_employee(text)
            if any(token in lowered for token in ("\u0441\u043c\u0435\u043d\u0438 \u0442\u0435\u043c\u0443", "\u0441\u043c\u0435\u043d\u0438\u0442\u044c \u0442\u0435\u043c\u0443", "change theme")):
                return self._set_setting(text, "theme", ("theme", "\u0442\u0435\u043c\u0443"))
            if any(token in lowered for token in ("\u0441\u043c\u0435\u043d\u0438 \u044f\u0437\u044b\u043a", "\u0441\u043c\u0435\u043d\u0438\u0442\u044c \u044f\u0437\u044b\u043a", "change language")):
                return self._set_language(text)
            if any(token in lowered for token in ("\u0437\u0432\u0443\u043a", "sound")):
                return self._set_sound(text)
            if any(token in lowered for token in ("\u0437\u0430\u043f\u0443\u0441\u0442\u0438 \u0446\u0435\u043b\u044c", "\u0441\u043e\u0437\u0434\u0430\u0439 \u0446\u0435\u043b\u044c", "\u043d\u043e\u0432\u0430\u044f \u0446\u0435\u043b\u044c", "start goal")):
                return self._goal(text, organization_id, "create")
            if any(token in lowered for token in ("\u043e\u0442\u043c\u0435\u043d\u0438 \u0446\u0435\u043b\u044c", "\u043e\u0441\u0442\u0430\u043d\u043e\u0432\u0438 \u0446\u0435\u043b\u044c", "cancel goal")):
                return self._goal(text, organization_id, "cancel")
            if any(token in lowered for token in ("\u043f\u0435\u0440\u0435\u043f\u043b\u0430\u043d\u0438\u0440\u0443\u0439", "replan")):
                return self._goal(text, organization_id, "replan")
            if any(token in lowered for token in ("\u043e\u0434\u043e\u0431\u0440\u0438", "approve")):
                return self._goal(text, organization_id, "approve")
            if any(token in lowered for token in ("\u043f\u043e\u043a\u0430\u0436\u0438 \u0446\u0435\u043b\u0438", "\u043f\u043e\u043a\u0430\u0436\u0438 \u0441\u0442\u0430\u0442\u0443\u0441", "\u0441\u0442\u0430\u0442\u0443\u0441 \u0446\u0435\u043b\u0438", "list goals", "status")):
                plans = self.supervisor_service.list_plans(organization_id)
                return SupervisorChatResult(True, self._plans_text(plans), action="list_goals", data={"count": len(plans)})

            if route == "STRONG" and self.strong_handler is not None:
                answer = self.strong_handler(text, organization_id)
                failed = not answer or str(answer).startswith("Strong provider не смог")
                return SupervisorChatResult(not failed, answer or "Strong provider не вернул ответ.", route="STRONG", action="strong")
            if any(token in lowered for token in ("создай организацию", "create organization")):
                return self._create_organization(text)
            if any(token in lowered for token in ("создай команду", "create team", "наним")):
                return self._create_team(text, organization_id)
            if any(token in lowered for token in ("удали сотрудника", "уволь", "delete employee", "fire")):
                return self._delete_employee(text)
            if any(token in lowered for token in ("переназнач", "replace employee", "замени сотрудника")):
                return self._reassign_employee(text)
            if any(token in lowered for token in ("смени тему", "сменить тему", "change theme")):
                return self._set_setting(text, "theme", ("theme", "тему"))
            if any(token in lowered for token in ("смени язык", "сменить язык", "change language")):
                return self._set_language(text)
            if any(token in lowered for token in ("звук", "sound")):
                return self._set_sound(text)
            if any(token in lowered for token in ("запусти цель", "создай цель", "новая цель", "start goal")):
                return self._goal(text, organization_id, "create")
            if any(token in lowered for token in ("отмени цель", "останови цель", "cancel goal")):
                return self._goal(text, organization_id, "cancel")
            if any(token in lowered for token in ("перепланируй", "replan")):
                return self._goal(text, organization_id, "replan")
            if any(token in lowered for token in ("одобри", "approve")):
                return self._goal(text, organization_id, "approve")
            if any(token in lowered for token in ("покажи цели", "покажи статус", "статус цели", "list goals", "status")):
                plans = self.supervisor_service.list_plans(organization_id)
                return SupervisorChatResult(True, self._plans_text(plans), action="list_goals", data={"count": len(plans)})
            if route == "STRONG":
                return SupervisorChatResult(False, "Для этого запроса нужен Strong provider, но он не подключён.", route=route, action="strong_unavailable")
            if organization_id is None:
                return SupervisorChatResult(
                    True,
                    "Понял задачу. Давайте сначала соберём подходящую команду, а затем превратим результат в рабочую цель.",
                    action="team_proposal",
                    data={"brief": text},
                )
            return SupervisorChatResult(True, "Понял запрос. Уточните, какую цель или действие нужно выполнить.", action="help")
        except (ValueError, KeyError, RuntimeError) as exc:
            return SupervisorChatResult(False, f"Не выполнено: {exc}", route=route, action="error")

    def confirm(self, token: str) -> SupervisorChatResult:
        pending = self._pending.pop(token, None)
        if pending is None:
            return SupervisorChatResult(False, "Подтверждение устарело или уже выполнено.", action="confirmation_expired")
        return self.handle(pending[0], pending[1], confirmed=True)

    def _route(self, text: str) -> str:
        if self._COMPLEX.search(text) or self._COMPLEX_RU.search(text):
            return "STRONG"
        if self.local_runtime is not None:
            try:
                decision = str(self.local_runtime.decide(text)).upper()
                return "LOCAL" if decision in {"SIMPLE", "SOCIAL", "LOCAL"} else "STRONG"
            except Exception:
                pass
        return "LOCAL"

    def _create_organization(self, text: str) -> SupervisorChatResult:
        if self.universal_service is None:
            raise RuntimeError("сервис организаций недоступен")
        name = re.sub(r".*?(?:создай организацию|create organization)\s*", "", text, flags=re.I).strip(" :.-") or "Новая организация"
        org = self.universal_service.create_organization(name)
        return SupervisorChatResult(True, f"Организация «{org.name}» создана.", route="STRONG", action="create_organization", data={"organization_id": org.organization_id})

    def _create_team(self, text: str, organization_id: str | None) -> SupervisorChatResult:
        if self.universal_service is None:
            raise RuntimeError("сервис команд недоступен")
        templates = self.universal_service.list_templates()
        if not templates:
            raise RuntimeError("нет доступного шаблона команды")
        template = next((item for item in templates if item.name.casefold() in text.casefold()), templates[0])
        name = text.split(":", 1)[1].strip() if ":" in text else f"{template.name} team"
        activation = self.universal_service.activate_template(template.template_id, name)
        return SupervisorChatResult(True, f"Команда «{activation.organization.name}» создана по шаблону «{template.name}».", route="STRONG", action="create_team", data={"organization_id": activation.organization.organization_id, "employee_ids": list(activation.employee_ids)})

    def _delete_employee(self, text: str) -> SupervisorChatResult:
        if self.management_service is None:
            raise RuntimeError("сервис сотрудников недоступен")
        agent_id = self._last_identifier(text)
        self.management_service.delete_agent(agent_id, "ORGANIZATION_OWNER", confirmed=True)
        return SupervisorChatResult(True, f"Сотрудник {agent_id} удалён.", route="STRONG", action="delete_employee")

    def _reassign_employee(self, text: str) -> SupervisorChatResult:
        if self.management_service is None:
            raise RuntimeError("сервис сотрудников недоступен")
        agent_id = self._last_identifier(text)
        role_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
        role_id = next((token.upper() for token in reversed(role_tokens) if token.lower() != agent_id.lower()), "CUSTOM_ROLE")
        database = getattr(self.management_service, "database", None)
        if database is None:
            raise RuntimeError("база данных недоступна")
        database.replace_agent_roles(agent_id, [role_id], "ORGANIZATION_OWNER", "Supervisor reassignment")
        return SupervisorChatResult(True, f"Сотруднику {agent_id} назначена роль {role_id}.", route="STRONG", action="reassign_employee", data={"agent_id": agent_id, "role_id": role_id})

    def _goal(self, text: str, organization_id: str | None, operation: str) -> SupervisorChatResult:
        if not organization_id:
            raise ValueError("не выбрана организация")
        if operation == "create":
            goal = re.sub(r".*?(?:создай цель|новая цель|запусти цель|start goal)\s*", "", text, flags=re.I).strip(" :.-")
            plan = self.supervisor_service.director(organization_id, goal)
        else:
            plans = self.supervisor_service.list_plans(organization_id)
            if not plans:
                raise ValueError("активных целей нет")
            plan = next((item for item in reversed(plans) if item.status not in {"COMPLETED", "CANCELLED"}), plans[-1])
            operation_handler = {
                "cancel": self.supervisor_service.cancel,
                "approve": self.supervisor_service.approve,
                "replan": self.supervisor_service.replan,
            }.get(operation)
            if operation_handler is not None:
                plan = operation_handler(plan.plan_id)
        return SupervisorChatResult(True, f"Цель «{plan.goal}»: {plan.status}.", route="STRONG", action=f"goal_{operation}", data={"plan_id": plan.plan_id})

    def _set_language(self, text: str) -> SupervisorChatResult:
        value = "uk" if "укра" in text.casefold() or re.search(r"\buk\b", text, re.I) else "en" if "англ" in text.casefold() or re.search(r"\ben\b", text, re.I) else "ru"
        self.settings["interface_language"] = value
        self.save_settings(self.settings)
        return SupervisorChatResult(True, f"Язык интерфейса изменён: {value}.", action="set_language", data={"language": value})

    def _set_sound(self, text: str) -> SupervisorChatResult:
        enabled = not any(token in text.casefold() for token in ("выключ", "отключ", "off"))
        self.settings["message_sounds_enabled"] = enabled
        self.save_settings(self.settings)
        return SupervisorChatResult(True, f"Звуки {'включены' if enabled else 'выключены'}.", action="set_sound")

    def _set_setting(self, text: str, key: str, markers: tuple[str, ...]) -> SupervisorChatResult:
        value = text.split()[-1].strip(".,:;!?'").lower()
        self.settings[key] = value
        self.save_settings(self.settings)
        return SupervisorChatResult(True, f"Настройка «{key}» изменена на «{value}».", action=f"set_{key}", data={key: value})

    @staticmethod
    def _last_identifier(text: str) -> str:
        matches = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text)
        if not matches:
            raise ValueError("не указан ID сотрудника")
        return next((item for item in matches if item.lower().startswith("agent-")), matches[-1])

    @staticmethod
    def _plans_text(plans: list[Any]) -> str:
        if not plans:
            return "Целей пока нет."
        return "\n".join(f"{item.plan_id}: {item.goal} — {item.status}" for item in plans[-10:])
