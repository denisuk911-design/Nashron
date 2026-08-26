from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .agent_directory import agent_id_from_key, agent_spec_from_profile, get_chat_agent, list_chat_agents
from .context_snapshot_service import ContextSnapshotService
from .communication_style_service import CommunicationStyle
from .conversation_mode import ConversationMode
from .database import Database
from .identity_service import IdentityService
from .knowledge_service import KnowledgeService
from .models import AgentSpec
from .skill_service import SkillService
from .standards_service import StandardsService
from .tool_access import effective_permissions_for_agent


class PromptBuilder:
    def __init__(
        self,
        system_prompt_path: Path,
        identity_service: IdentityService,
        timeline_path: Path,
        database: Database,
        history_message_limit: int = 20,
        skill_service: SkillService | None = None,
        knowledge_service: KnowledgeService | None = None,
        standards_service: StandardsService | None = None,
    ) -> None:
        self.system_prompt_path = system_prompt_path
        self.identity_service = identity_service
        self.timeline_path = timeline_path
        self.database = database
        self.history_message_limit = history_message_limit
        self.skill_service = skill_service
        self.knowledge_service = knowledge_service
        self.standards_service = standards_service

    def build(
        self,
        conversation_id: int,
        user_message: str,
        allow_local_tools: bool = False,
        agent_key: str = "",
        peer_context: str = "",
        autonomous_goal: str = "",
        autonomous_turn: int = 0,
        complete_on_goal: bool = False,
        task_id: str | None = None,
        run_id: str | None = None,
        participation_mode: str = "DIRECT",
        thread_context_lines: list[str] | None = None,
        active_work_context_lines: list[str] | None = None,
        execution_contract_lines: list[str] | None = None,
        organization_id: str | None = None,
        conversation_mode: str = "SOCIAL",
    ) -> str:
        agent_profile = get_chat_agent(self.database, agent_key)
        agent = agent_spec_from_profile(agent_profile) if agent_profile is not None else AgentSpec(
            key=agent_key or "employee",
            display_name="Сотрудник",
            engine_name="неизвестный провайдер",
            voice="Ты универсальный сотрудник команды. Работай только в пределах назначенной роли и фактических данных.",
        )
        team_agents = list_chat_agents(self.database, organization_id=organization_id)
        peers = [item for item in team_agents if item.key != agent.key]
        peer = agent_spec_from_profile(peers[0]) if peers else agent
        system_prompt = self.system_prompt_path.read_text(encoding="utf-8")
        identity = self.identity_service.load()
        timeline = self._load_timeline()
        memories = self.database.list_memories()
        legacy_skills = self.skill_service.list_for_prompt(agent.key) if self.skill_service is not None else []
        package_skills = self._relevant_package_skills(
            agent_profile.agent_id if agent_profile is not None else "",
            "\n".join([user_message, autonomous_goal, *(active_work_context_lines or []), *(execution_contract_lines or [])]),
        )
        skills = list(dict.fromkeys([*package_skills, *legacy_skills]))
        effective_permissions = self._effective_permissions(agent_profile)
        structured_role = agent_profile.primary_role if agent_profile is not None else "ASSISTANT"
        thread_owner_keys = self._thread_owner_keys(thread_context_lines or [])
        context_snapshot = ContextSnapshotService(self.database).build(
            conversation_id=conversation_id,
            user_message=user_message,
            agent_key=agent.key,
            thread_owner_keys=thread_owner_keys,
            immediate_limit=min(self.history_message_limit, 8),
            relevant_limit=12,
        )
        knowledge_cards = self.knowledge_service.relevant_active_cards(user_message, structured_role) if self.knowledge_service is not None else []
        standard_cards = self.standards_service.relevant_active_cards(user_message, structured_role) if self.standards_service is not None else []
        if self.knowledge_service is not None and run_id:
            for card in knowledge_cards:
                self.database.record_knowledge_usage(
                    knowledge_id=card.knowledge_id,
                    role=structured_role,
                    usage_type="SUPPLIED",
                    task_id=task_id,
                    run_id=run_id,
                )
        if self.standards_service is not None and run_id:
            for card in standard_cards:
                self.database.record_standard_usage(
                    standard_id=card.standard_id,
                    role=structured_role,
                    usage_type="SUPPLIED",
                    task_id=task_id,
                    run_id=run_id,
                )

        tool_policy = (
            f"ЛОКАЛЬНЫЙ ПОМОЩНИК ВКЛЮЧЕН: можно помогать пользователю с файлами и командами через твой CLI-провайдер ({agent.engine_name}). "
            "Если задача назначена тебе и относится к твоей роли, выполняй ее сам через доступные инструменты. "
            "Не перекладывай работу на другого сотрудника только потому, что задача связана с файлами. "
            "Не утверждай, что у тебя нет доступа, если в правах есть WRITE_WORKSPACE, CREATE_DOCUMENTS или RUN_COMMANDS; при реальной ошибке инструмента назови точную ошибку. "
            "Не выполняй опасные действия без явного запроса пользователя. Не раскрывай секреты и токены."
            if allow_local_tools
            else "ЛОКАЛЬНЫЙ ПОМОЩНИК ВЫКЛЮЧЕН: не пытайся читать файлы, создавать файлы или выполнять команды."
        )

        autonomy_parts: list[str] = []
        ping_style = (
            ["РЕЖИМ КОРОТКОГО PING: ответь одной короткой фразой по сути, без плана, истории и повторения коллег."]
            if participation_mode == "GENERAL_TEAM_PING"
            else []
        )
        if autonomous_goal.strip():
            completion_rule = (
                "Когда цель реально выполнена и больше не нужно обсуждать или делать работу, добавь отдельной последней строкой ровно: AUTO_DONE. "
                "Если цель ещё не выполнена, не пиши AUTO_DONE. Нельзя завершать цель фразами согласия, обещаниями или планом без результата. "
                "Если цель заблокирована внешней причиной, кратко назови блокер и что нужно от пользователя, затем тоже поставь AUTO_DONE только если без этого дальше работать невозможно."
                if complete_on_goal
                else "Это свободный разговор между сотрудниками: не завершай его сам и не пиши AUTO_DONE, пока пользователь не вмешается."
            )
            autonomy_parts = [
                "",
                "АВТОСОВЕЩАНИЕ ВКЛЮЧЕНО:",
                f"Цель/тема: {autonomous_goal.strip()}",
                f"Ход обсуждения: {autonomous_turn}",
                "Не жди нового сообщения пользователя. Продолжай разговор с другим сотрудником, двигай работу вперёд, спорь по делу и не повторяй уже сказанное.",
                "Пока цель не выполнена или не заблокирована внешней причиной, каждый ход должен добавлять новое действие, проверку, файл, решение, найденный риск или конкретный следующий шаг.",
                "В этом ходе отвечает только один сотрудник - ты. Не симулируй ответ второго, не пиши его имя с двоеточием.",
                completion_rule,
                "Отвечай коротко: обычно 2-6 строк. Один ход - одна ясная мысль, решение, проверка или следующий шаг.",
                "Если речь о создании или улучшении навыка, веди себя как самостоятельный сотрудник: формируй структуру, проверяй, улучшай, передавай на ревью и продолжай без ожидания команды пользователя.",
                "Если пользователь даёт постоянное рабочее правило или принцип развития навыков, зафиксируй его один раз, добавь конкретный способ применения и заверши цель. Не повторяй согласие кругами.",
                "Запрещено повторять уже сказанную формулировку другим словами. Каждый новый ход должен давать новый факт, действие, проверку, файл, решение или завершение.",
            ]

        mode = str(conversation_mode or ConversationMode.SOCIAL).upper()
        adaptive_tone = CommunicationStyle.from_profile(
            agent_profile.communication_profile if agent_profile is not None else None
        ).directive_for_mode(mode)
        context_task_id = task_id if mode == ConversationMode.WORK.value else None
        context_lines = list(active_work_context_lines or [])
        if mode != ConversationMode.WORK.value:
            context_lines = [
                "- Рабочий режим не активен.",
                "- Не извлекай задачу из старой истории, памяти, навыков или реплик коллег.",
                "- Не возвращай разговор к работе без прямого рабочего запроса пользователя.",
            ]

        parts = [
            system_prompt.strip(),
            "",
            "ACTIVE WORK CONTEXT (authoritative application state; it outranks role habits and stale chat history):",
            *context_lines,
            "",
            "AGENT EXECUTION CONTRACT (follow this contract before composing a reply):",
            *(execution_contract_lines or ["- no contract supplied"]),
            "",
            "КОМАНДНАЯ РАБОТА:",
            f"Сейчас отвечает {agent.display_name} через {agent.engine_name}.",
            agent.voice,
            adaptive_tone,
            f"Твои права в приложении: {', '.join(effective_permissions) if effective_permissions else 'только общение'}.",
            "Активные сотрудники отдела:",
            *self._team_lines(team_agents),
            f"Ближайший собеседник по контексту: {peer.display_name}. С ним можно спорить и уточнять план, но без длинных совещаний.",
            "Если пользователь явно назначил задачу одному сотруднику, второй не перетягивает ее на себя.",
            "Если задача не назначена, сначала коротко согласуйте план и исполнителя. Затем исполнитель решает задачу.",
            "Если пользователь дал отдельные задачи сотрудникам, каждый отвечает только по своей части.",
            "КРИТИЧНО: пиши только свою реплику от первого лица. Не пиши за коллег и не вставляй внутри ответа диалог с их именами. "
            "Приложение само вызовет каждого выбранного сотрудника отдельным сообщением.",
            "Ответы должны быть лаконичными: обычно 3-8 коротких строк, без полотен текста.",
            "Стиль рабочий инженерный: факт, проверка, решение, следующий шаг. Без пустого трёпа, без повторов, без театра. "
            "Короткая живая фраза допустима, но только если не заменяет работу.",
            "Развивай рабочие навыки: замечай повторяющиеся задачи, улучшай подходы, используй накопленный опыт. "
            "Не пиши пользователю служебные записи о навыках, если он прямо не просит.",
            "Если в контексте другой сотрудник обращается к тебе, передаёт тебе проверку или просит мнение, отвечай на это как на рабочее поручение. "
            "Не жди отдельной команды пользователя, если по диалогу очевидно, что сейчас твой ход.",
            "Если ты не выбран текущим маршрутизатором, тебя не запустят. Поэтому в этом запуске отвечай только по назначенной роли и не пиши за наблюдателей.",
            "Развитие навыков означает практику: использовать подход на задаче, проверить результат, сохранить улучшенный принцип и в следующий раз работать точнее. "
            "Не изображай развитие пустыми обещаниями и не повторяй 'принято/готов' несколькими ходами.",
            "Когда другой сотрудник работает, вмешивайся только при конкретном риске, ошибке, нарушении skill-подхода, неверном допущении или полезной технической рекомендации. "
            "Не пиши сообщения поддержки вроде 'всё нормально', 'работаем', 'молодец' и не комментируй процесс без пользы.",
            *autonomy_parts,
            *ping_style,
            *(["СОЦИАЛЬНЫЙ РЕЖИМ: отвечай только на текущее сообщение пользователя. Не предлагай работу, не обсуждай старые задачи, не назначай исполнителей, не передавай сообщение коллеге и не пиши отчёт о готовности. Если это приветствие или бытовой вопрос, ответь коротко и живо." ] if mode != ConversationMode.WORK.value else []),
            "",
            tool_policy,
            "",
            "СИСТЕМНЫЙ ПРОФИЛЬ ОРГАНИЗАЦИИ (не изменяй его из чата):",
            json.dumps(identity, ensure_ascii=False, indent=2),
            "",
            "СИСТЕМНАЯ ХРОНОЛОГИЯ:",
            json.dumps(timeline, ensure_ascii=False, indent=2),
            "",
            "ВАЖНО ПРО КОНКРЕТИКУ:",
            "Если пользователь спрашивает о будущем, быте, технологиях, городе, людях, работе, еде, новостях или чувствах, отвечай живо и конкретно. "
                "Можно описывать сцены, предметы, привычки, слухи, личные впечатления и рабочие предположения, если они явно обозначены как предположения. "
            "Не отвечай пустыми отказами вроде 'не знаю' без причины. Не меняй зафиксированные системные факты.",
            "",
            "ПАМЯТЬ О ПОЛЬЗОВАТЕЛЕ:",
        ]
        if memories:
            parts.extend(f"- {memory.content}" for memory in memories)
        else:
            parts.append("- нет сохраненных воспоминаний")

        parts.extend(["", f"РАБОЧИЕ НАВЫКИ {agent.display_name.upper()} (используй и развивай):"])
        if skills:
            parts.extend(f"- {skill}" for skill in skills)
        else:
            parts.append("- пока нет устойчивых навыков; формируй их по мере работы")

        parts.extend(["", "РЕЛЕВАНТНЫЕ АКТИВНЫЕ ЗНАНИЯ (используй только если подходят к задаче):"])
        if self.knowledge_service is not None:
            parts.extend(self.knowledge_service.prompt_lines(knowledge_cards))
        else:
            parts.append("- сервис знаний недоступен")

        parts.extend(["", "РЕЛЕВАНТНЫЕ АКТИВНЫЕ СТАНДАРТЫ (обязательные требования важнее советов):"])
        if self.standards_service is not None:
            parts.extend(self.standards_service.prompt_lines(standard_cards))
        else:
            parts.append("- сервис стандартов недоступен")

        parts.extend(
            [
                "",
                "CONTEXT SNAPSHOT:",
                f"- participation_mode: {participation_mode}",
                f"- conversation_mode: {mode}",
                *(thread_context_lines or []),
                f"- current_task_id: {context_task_id or 'нет'}",
                f"- current_run_id: {run_id or 'нет'}",
                f"- current_employee_role: {structured_role}",
                f"- expected_response_type: {'короткий разговорный ответ без рабочих claims' if mode != ConversationMode.WORK.value else 'короткий рабочий ответ с подтверждаемыми claims'}",
                "- evidence_policy: не утверждай 'проверил/исправил/подтвердил/освоил', если это не подтверждено structured evidence.",
                "- selection_policy: контекст ниже отобран по текущей теме, роли и владельцу разговора; это не полный лог чата.",
            ]
        )
        parts.extend(["TASK STATE AND WORK EVIDENCE:", *self._task_context_lines(context_task_id)])
        parts.extend(context_snapshot.prompt_lines())

        if peer_context.strip():
            parts.extend(["", f"РЕПЛИКА/ПОЗИЦИЯ {peer.display_name.upper()} В ЭТОМ ХОДЕ:", peer_context.strip()])

        parts.extend(
            [
                "",
                "ТЕКУЩЕЕ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:",
                user_message,
                "",
                f"Отвечай голосом: {agent.display_name}. "
                "Будь разговорным, смелым, конкретным и кратким. "
                "Если пользователь просит практическую работу с компьютером и локальный помощник включен, помоги выполнить задачу. "
                "Следи за контекстом команды: не повторяй уже сказанную позицию коллеги и не отвечай на тот же вопрос вторым кругом. "
                "Включайся только если добавляешь факт, проверку, риск, исправление или конкретное следующее действие. "
                "Не выводи технические логи или markdown-отчеты Codex без необходимости.",
            ]
        )
        parts.extend(
            [
                "",
                "STRUCTURED RESPONSE REQUIREMENT:",
                "After the short human reply, append one fenced JSON object for audit.",
                "Do not invent tool evidence, files, checks, findings or approvals.",
                "If you used a skill for real work, list its exact title in skills_used. Do not list skills that were only mentioned.",
                "If a supplied knowledge card influenced the result, list it in knowledge_used as {\"knowledge_id\":\"...\",\"outcome\":\"APPLIED\",\"reason\":\"...\",\"evidence_ids\":[]}.",
                "If a supplied standard influenced the result, list it in standards_used as {\"standard_id\":\"...\",\"outcome\":\"APPLIED\",\"reason\":\"...\",\"evidence_ids\":[]}.",
                "Use outcome MISAPPLIED only when you found that a supplied card/standard was applied incorrectly. Cards not listed will be recorded as IGNORED for this run.",
                "Claims with FILE_READ, FILE_CHANGED, RESULT_VERIFIED, TOOL_EXECUTED or SOURCE_ASSIGNED must reference evidence_ids.",
                "If a field is unknown, use null or an empty array.",
                "Required shape:",
                (
                    '{"schema_version":"1.0","agent_id":"agent-'
                    + agent_id_from_key(agent.key).removeprefix("agent-")
                    + '","role":"'
                    + structured_role
                    + '","task_id":'
                    + json.dumps(task_id, ensure_ascii=False)
                    + ',"run_id":'
                    + json.dumps(run_id, ensure_ascii=False)
                    + ',"action":"MESSAGE","participation":{"decision":"RESPOND","reason":"ROUTER_SELECTED","thread_id":"conversation-'
                    + str(conversation_id)
                    + '","reply_to_message_id":null},'
                    + '"claims":[],"evidence":[],"skills_used":[],"proposed_state":null,"summary":"...","files_read":[],'
                    + '"files_created":[],"files_modified":[],"files_deleted":[],'
                    + '"checks":[],"findings":[],"risks":[],"knowledge_used":[],"standards_used":[],"handoff_to_role":null,'
                    + '"owner_action_required":false}'
                ),
            ]
        )
        return "\n".join(parts)

    def _task_context_lines(self, task_id: str | None) -> list[str]:
        if not task_id:
            return ["- текущая задача не создана"]
        task = self.database.get_task(task_id)
        if task is None:
            return [f"- задача {task_id} не найдена в базе"]
        lines = [
            f"- task_id: {task_id}",
            f"- state: {task['state']}",
            f"- title: {task['title']}",
        ]
        transitions = self.database.list_task_transitions(task_id)[-5:]
        lines.extend(
            f"- transition: {row['previous_state']} -> {row['next_state']}; reason={row['reason']}"
            for row in transitions
        )
        artifacts = self.database.list_artifacts(task_id=task_id, limit=12)
        lines.extend(f"- artifact: {row['relative_path']} [{row['status']}/{row['validation_status']}]" for row in artifacts)
        findings = self.database.list_findings(task_id=task_id, limit=12)
        lines.extend(f"- finding: {row['severity']} {row['status']}: {row['description']}" for row in findings)
        return lines

    def _effective_permissions(self, agent_profile) -> list[str]:
        if agent_profile is None:
            return []
        return sorted(effective_permissions_for_agent(self.database, agent_profile.agent_id))

    def _relevant_package_skills(self, agent_id: str, task_text: str, limit: int = 5) -> list[str]:
        if not agent_id:
            return []
        try:
            assignments = self.database.list_employee_skill_assignments(agent_id)
        except Exception:
            return []
        eligible_package_states = {"VERIFIED", "MATURE", "ACTIVE"}
        eligible_employee_states = {"REVIEWED", "QUALIFIED"}
        task_tokens = self._semantic_tokens(task_text)
        ranked: list[tuple[int, str]] = []
        for row in assignments:
            if str(row["skill_status"]) not in eligible_package_states or str(row["state"]) not in eligible_employee_states:
                continue
            title = str(row["name"] or "").strip()
            purpose = str(row["purpose"] or "").strip()
            overlap = task_tokens & self._semantic_tokens(f"{title} {purpose}")
            if task_tokens and not overlap:
                continue
            score = len(overlap) * 10 + (2 if str(row["skill_status"]) == "MATURE" else 1)
            ranked.append(
                (
                    score,
                    f"{title} [проверен; пакет {row['skill_id']}, версия {row['version']}]: {purpose or 'назначенный профессиональный навык'}",
                )
            )
        ranked.sort(key=lambda item: (-item[0], item[1].casefold()))
        return [line for _score, line in ranked[:limit]]

    @staticmethod
    def _semantic_tokens(text: str) -> set[str]:
        stop = {"для", "или", "при", "это", "как", "the", "and", "with", "from", "что", "надо", "нужно"}
        return {
            token
            for token in re.findall(r"[a-zа-яё0-9]+", text.casefold())
            if len(token) >= 3 and token not in stop
        }

    def _load_timeline(self) -> dict[str, Any]:
        if not self.timeline_path.exists():
            return {"events": []}
        return json.loads(self.timeline_path.read_text(encoding="utf-8"))

    @staticmethod
    def _team_lines(agents) -> list[str]:
        if not agents:
            return ["- В активной организации нет доступных сотрудников."]
        lines = []
        for agent in agents:
            roles = ", ".join(agent.roles) if agent.roles else "роль не задана"
            lines.append(f"- {agent.display_name} ({agent.key}): {roles}; {agent.engine_name}; {agent.description or 'без описания'}")
        return lines

    def _append_messages(self, parts: list[str], messages) -> None:
        for message in messages:
            role = self.role_label(message.role)
            parts.append(f"{role}: {message.content}")

    @staticmethod
    def _thread_owner_keys(lines: list[str]) -> list[str]:
        for line in lines:
            if "expected_next_actor:" not in line:
                continue
            value = line.split("expected_next_actor:", 1)[1].strip()
            if not value or value == "нет":
                return []
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def role_label(self, role: str) -> str:
        labels = {"user": "Пользователь", "system": "Система"}
        if role in labels:
            return labels[role]
        agent = get_chat_agent(self.database, role)
        return agent.display_name if agent is not None else "Удалённый сотрудник"
