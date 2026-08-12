from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable

from .agent_directory import agent_id_from_key
from .database import Database


class IntentType(StrEnum):
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    FORMAT = "FORMAT"
    REVIEW = "REVIEW"
    VERIFY = "VERIFY"
    INSPECT = "INSPECT"
    EXPLAIN = "EXPLAIN"
    CONTINUE = "CONTINUE"
    HANDOFF = "HANDOFF"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ASK_STATUS = "ASK_STATUS"
    TEAM_DISCUSSION = "TEAM_DISCUSSION"
    MANAGEMENT = "MANAGEMENT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class UserIntent:
    intent: IntentType
    operation: str
    explicit_agent_keys: tuple[str, ...] = ()
    artifact_query: str = ""
    confidence: str = "MEDIUM"
    clarification_required: bool = False
    handoff_requested: bool = False


@dataclass(frozen=True)
class ActiveWorkContext:
    conversation_id: int
    thread_id: str
    task_id: str | None = None
    task_title: str = ""
    task_goal: str = ""
    current_owner_agent_id: str | None = None
    previous_owner_agent_id: str | None = None
    active_artifact_ids: tuple[str, ...] = ()
    primary_artifact_id: str | None = None
    artifact_type: str = ""
    source_agent_id: str | None = None
    current_operation: str = "UNKNOWN"
    expected_output_type: str = ""
    unresolved_questions: tuple[str, ...] = ()
    last_completed_action: str = ""
    last_user_intent: str = "UNKNOWN"
    handoff_state: str = "NONE"
    status: str = "CURRENT"
    updated_at: str = ""

    def to_lines(self) -> list[str]:
        return [
            f"- status: {self.status}",
            f"- conversation_id/thread_id: {self.conversation_id}/{self.thread_id}",
            f"- task_id/title: {self.task_id or 'нет'} / {self.task_title or 'нет'}",
            f"- task_goal: {self.task_goal or 'нет'}",
            f"- current_owner/previous_owner: {self.current_owner_agent_id or 'нет'} / {self.previous_owner_agent_id or 'нет'}",
            f"- active_artifacts: {', '.join(self.active_artifact_ids) or 'нет'}",
            f"- primary_artifact/type/source: {self.primary_artifact_id or 'нет'} / {self.artifact_type or 'нет'} / {self.source_agent_id or 'нет'}",
            f"- operation/expected_output: {self.current_operation} / {self.expected_output_type or 'нет'}",
            f"- last_completed_action: {self.last_completed_action or 'нет'}",
            f"- last_user_intent/handoff: {self.last_user_intent} / {self.handoff_state}",
            f"- unresolved_questions: {'; '.join(self.unresolved_questions) or 'нет'}",
        ]


@dataclass(frozen=True)
class ArtifactReference:
    artifact_ids: tuple[str, ...] = ()
    primary_artifact_id: str | None = None
    artifact_type: str = ""
    source_agent_id: str | None = None
    reason: str = "NONE"
    ambiguous: bool = False


@dataclass(frozen=True)
class AgentExecutionContract:
    contract_id: str
    conversation_id: int
    task_id: str | None
    run_id: str | None
    agent_id: str
    role: str
    user_instruction: str
    intent: str
    input_artifact_ids: tuple[str, ...]
    required_operation: str
    expected_output: str
    expected_output_type: str
    allowed_tools: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ()
    completion_criteria: tuple[str, ...] = ()
    forbidden_substitutions: tuple[str, ...] = ()
    clarification_required: bool = False

    def to_lines(self) -> list[str]:
        return [
            f"- contract_id: {self.contract_id}",
            f"- agent/role: {self.agent_id} / {self.role}",
            f"- intent/operation: {self.intent} / {self.required_operation}",
            f"- input_artifacts: {', '.join(self.input_artifact_ids) or 'нет'}",
            f"- expected_output/type: {self.expected_output or 'нет'} / {self.expected_output_type or 'нет'}",
            f"- completion_criteria: {'; '.join(self.completion_criteria) or 'проверить фактический результат'}",
            f"- forbidden_substitutions: {'; '.join(self.forbidden_substitutions) or 'нет'}",
            f"- clarification_required: {'да' if self.clarification_required else 'нет'}",
        ]


@dataclass(frozen=True)
class OutputValidation:
    accepted: bool
    code: str
    message: str = ""


class IntentResolver:
    def resolve(self, text: str, agent_names: dict[str, Iterable[str]] | None = None) -> UserIntent:
        normalized = " ".join(str(text or "").lower().replace("ё", "е").split())
        explicit = self._explicit_agents(normalized, agent_names or {})
        artifact_query = "bom" if re.search(r"\bbom\b|б\s*о\s*м", normalized) else ""
        if any(token in normalized for token in ("останов", "стоп", "прекрати")):
            intent = IntentType.REJECT
        elif any(token in normalized for token in ("что в нем", "что в нём", "содержит", "покажи содержимое")):
            intent = IntentType.INSPECT
        elif any(token in normalized for token in ("оформля", "оформи", "форматир", "подготовь документ")):
            intent = IntentType.FORMAT
        elif any(token in normalized for token in ("проверь", "проверить", "ревью", "аудит")):
            intent = IntentType.REVIEW
        elif any(token in normalized for token in ("исправь", "исправляй", "переделай", "измени", "замечани")):
            intent = IntentType.MODIFY
        elif any(token in normalized for token in ("объясни", "обьясни", "почему", "расскажи")):
            intent = IntentType.EXPLAIN
        elif any(token in normalized for token in ("статус", "как там", "что сделано")):
            intent = IntentType.ASK_STATUS
        elif any(token in normalized for token in ("одобряю", "утверждаю", "принято")):
            intent = IntentType.APPROVE
        elif any(token in normalized for token in ("команда", "обсудите", "между собой")):
            intent = IntentType.TEAM_DISCUSSION
        elif any(token in normalized for token in ("продолжай", "дальше", "продолжить")):
            intent = IntentType.CONTINUE
        elif any(token in normalized for token in ("создай", "сделай", "давай", "сформируй")) or artifact_query:
            intent = IntentType.CREATE
        else:
            intent = IntentType.UNKNOWN
        handoff = bool(explicit) and any(token in normalized for token in ("у романа", "у петра", "у шушан", "бери", "передай", "передавай"))
        return UserIntent(
            intent=intent,
            operation=intent.value,
            explicit_agent_keys=tuple(explicit),
            artifact_query=artifact_query,
            confidence="HIGH" if intent != IntentType.UNKNOWN else "LOW",
            handoff_requested=handoff,
        )

    @staticmethod
    def _explicit_agents(text: str, agent_names: dict[str, Iterable[str]]) -> list[str]:
        result: list[str] = []
        for key, names in agent_names.items():
            candidates = [key, *list(names)]
            if any(candidate and candidate.lower().replace("ё", "е") in text for candidate in candidates):
                result.append(key)
        return result


class ArtifactReferentResolver:
    def __init__(self, database: Database) -> None:
        self.database = database

    def resolve(self, text: str, context: ActiveWorkContext | None) -> ArtifactReference:
        normalized = " ".join(str(text or "").lower().replace("ё", "е").split())
        rows = self.database.list_artifacts(task_id=context.task_id if context else None)
        by_id = {str(row["id"]): row for row in rows}
        explicit = [row for row in rows if self._explicit_match(row, normalized)]
        source_hint = self._source_hint(normalized)
        if source_hint and explicit:
            owned = [row for row in explicit if self._owned_by(row, source_hint)]
            if owned:
                explicit = owned
        active = [by_id[item] for item in (context.active_artifact_ids if context else ()) if item in by_id]
        if explicit:
            return self._result(explicit, "EXPLICIT_ARTIFACT")
        # An explicit BOM request must never fall back to an unrelated memo.
        if "bom" in normalized or "б\u043e\u043c" in normalized:
            return ArtifactReference(reason="EXPLICIT_ARTIFACT_NOT_FOUND")
        if active:
            return self._result(active, "ACTIVE_CONTEXT")
        if context and context.primary_artifact_id:
            row = self.database.get_artifact(context.primary_artifact_id)
            if row is not None:
                return self._result([row], "PRIMARY_ARTIFACT")
        return ArtifactReference(reason="NONE", ambiguous=False)

    def _explicit_match(self, row: Any, text: str) -> bool:
        artifact_type = str(row["artifact_type"] or "").lower()
        path = str(row["relative_path"] or "").lower()
        payload = self.database.get_artifact_payload(str(row["id"]))
        title = str(payload["title"] if payload is not None else "").lower()
        if "bom" in text:
            return artifact_type == "bom" or "bom" in path or "bom" in title
        if "мемо" in text or "memo" in text:
            return "memo" in path or "memo" in title
        return False

    def _owned_by(self, row: Any, source_hint: str) -> bool:
        payload = self.database.get_artifact_payload(str(row["id"]))
        source = str(payload["source_agent_id"] if payload is not None else row["authoring_role"] or "").lower()
        return source_hint in source

    @staticmethod
    def _source_hint(text: str) -> str:
        return ""

    def _result(self, rows: list[Any], reason: str) -> ArtifactReference:
        ids = tuple(str(row["id"]) for row in rows)
        primary = ids[0] if ids else None
        payload = self.database.get_artifact_payload(primary) if primary else None
        source = str(payload["source_agent_id"]) if payload is not None and payload["source_agent_id"] else None
        return ArtifactReference(
            artifact_ids=ids,
            primary_artifact_id=primary,
            artifact_type=str(rows[0]["artifact_type"] or "") if rows else "",
            source_agent_id=source,
            reason=reason,
            ambiguous=len(ids) > 1,
        )


class HandoffService:
    """Structured transfer boundary between employees."""

    def __init__(self, database: Database, conversation_id: int) -> None:
        self.database = database
        self.conversation_id = conversation_id

    def create(self, **values: Any) -> str:
        values["conversation_id"] = self.conversation_id
        return self.database.create_work_handoff(values=values)

    def recent(self, limit: int = 20) -> list[Any]:
        return self.database.list_work_handoffs(self.conversation_id, limit=limit)


class OutputValidator:
    def validate(self, contract: AgentExecutionContract, content: str, artifact_rows: list[Any]) -> OutputValidation:
        expected = contract.expected_output_type.upper()
        text = str(content or "").lower()
        paths = " ".join(str(row["relative_path"] or "").lower() for row in artifact_rows)
        if expected == "BOM_DOCUMENT":
            if "memo" in text and "bom" not in text and not any("bom" in path for path in paths.split()):
                return OutputValidation(False, "OUTPUT_TYPE_MISMATCH", "Ожидался BOM-документ, получен служебный memo.")
            if paths and all("memo" in path for path in paths.split()):
                return OutputValidation(False, "OUTPUT_TYPE_MISMATCH", "Ожидался BOM-документ, зарегистрирован только memo.")
        return OutputValidation(True, "OK")


class WorkContextService:
    def __init__(self, database: Database, conversation_id: int, thread_id: str) -> None:
        self.database = database
        self.conversation_id = conversation_id
        self.thread_id = thread_id
        self.handoff_service = HandoffService(database, conversation_id)

    def get(self) -> ActiveWorkContext | None:
        row = self.database.get_active_work_context(self.conversation_id)
        if row is None:
            return None
        return self._from_row(row)

    def apply_command(
        self,
        *,
        text: str,
        intent: UserIntent,
        reference: ArtifactReference,
        selected_agent_keys: list[str],
        task_id: str | None = None,
    ) -> ActiveWorkContext:
        previous = self.get()
        owner = agent_id_from_key(selected_agent_keys[0]) if selected_agent_keys else (previous.current_owner_agent_id if previous else None)
        previous_owner = previous.current_owner_agent_id if previous and owner != previous.current_owner_agent_id else (previous.previous_owner_agent_id if previous else None)
        expected = self._expected_output(intent, reference)
        unresolved = ["Уточнить рабочий артефакт"] if intent.intent in {IntentType.FORMAT, IntentType.REVIEW, IntentType.MODIFY} and not reference.primary_artifact_id else []
        carries_previous_artifact = intent.intent in {
            IntentType.FORMAT,
            IntentType.REVIEW,
            IntentType.MODIFY,
            IntentType.INSPECT,
            IntentType.EXPLAIN,
            IntentType.CONTINUE,
            IntentType.HANDOFF,
        }
        values = {
            "thread_id": self.thread_id,
            "task_id": task_id or (previous.task_id if previous else None),
            "task_title": text[:160],
            "task_goal": text,
            "current_owner_agent_id": owner,
            "previous_owner_agent_id": previous_owner,
            "active_artifact_ids": list(reference.artifact_ids) or (list(previous.active_artifact_ids) if previous and carries_previous_artifact else []),
            "primary_artifact_id": reference.primary_artifact_id or (previous.primary_artifact_id if previous and carries_previous_artifact else None),
            "artifact_type": reference.artifact_type or (previous.artifact_type if previous and carries_previous_artifact else ""),
            "source_agent_id": reference.source_agent_id or (previous.source_agent_id if previous and carries_previous_artifact else None),
            "current_operation": intent.operation,
            "expected_output_type": expected,
            "unresolved_questions": unresolved,
            "last_completed_action": previous.last_completed_action if previous else "",
            "last_user_intent": intent.intent.value,
            "handoff_state": "REQUESTED" if intent.handoff_requested or (reference.source_agent_id and owner and reference.source_agent_id != owner) else (previous.handoff_state if previous else "NONE"),
            "status": "CURRENT",
        }
        self.database.upsert_active_work_context(conversation_id=self.conversation_id, values=values)
        context = self.get()
        assert context is not None
        self.database.log_event(
            "artifact_referent_resolution",
            f"conversation={self.conversation_id}; reason={reference.reason}; primary={reference.primary_artifact_id or 'none'}; ambiguous={reference.ambiguous}",
        )
        owner_changed = bool(previous and owner and owner != previous.current_owner_agent_id)
        if (intent.handoff_requested or owner_changed) and selected_agent_keys:
            self.handoff_service.create(
                task_id=context.task_id,
                from_agent_id=reference.source_agent_id or (previous.current_owner_agent_id if previous else None),
                to_agent_id=agent_id_from_key(selected_agent_keys[0]),
                artifact_ids=list(context.active_artifact_ids),
                requested_operation=intent.operation,
                expected_output="Выполнить текущую операцию над переданным артефактом",
                expected_output_type=expected,
                user_instruction=text,
            )
            self.database.log_event(
                "structured_handoff_created",
                f"conversation={self.conversation_id}; from={reference.source_agent_id or (previous.current_owner_agent_id if previous else 'none')}; to={selected_agent_keys[0]}; artifacts={','.join(context.active_artifact_ids)}",
            )
        return context

    def bind_task(self, task_id: str, title: str) -> ActiveWorkContext | None:
        context = self.get()
        if context is None:
            return None
        self.database.upsert_active_work_context(
            conversation_id=self.conversation_id,
            values={**context.__dict__, "task_id": task_id, "task_title": title},
        )
        return self.get()

    def create_contract(
        self,
        *,
        context: ActiveWorkContext,
        intent: UserIntent,
        user_instruction: str,
        agent_id: str,
        role: str,
        run_id: str,
        allowed_tools: list[str],
    ) -> AgentExecutionContract:
        criteria = self._criteria(context.expected_output_type)
        forbidden = ["не подменять активный артефакт memo или общим шаблоном", "не объявлять работу выполненной без результата"]
        contract_id = self.database.create_execution_contract(
            values={
                "conversation_id": self.conversation_id,
                "task_id": context.task_id,
                "run_id": run_id,
                "agent_id": agent_id,
                "role": role,
                "user_instruction": user_instruction,
                "intent": intent.intent.value,
                "input_artifact_ids": list(context.active_artifact_ids),
                "required_operation": context.current_operation,
                "expected_output": context.expected_output_type,
                "expected_output_type": context.expected_output_type,
                "allowed_tools": allowed_tools,
                "required_evidence": ["фактический файл или наблюдаемый результат"],
                "completion_criteria": criteria,
                "forbidden_substitutions": forbidden,
                "clarification_required": bool(context.unresolved_questions),
            }
        )
        return AgentExecutionContract(
            contract_id=contract_id,
            conversation_id=self.conversation_id,
            task_id=context.task_id,
            run_id=run_id,
            agent_id=agent_id,
            role=role,
            user_instruction=user_instruction,
            intent=intent.intent.value,
            input_artifact_ids=context.active_artifact_ids,
            required_operation=context.current_operation,
            expected_output=context.expected_output_type,
            expected_output_type=context.expected_output_type,
            allowed_tools=tuple(allowed_tools),
            required_evidence=("фактический файл или наблюдаемый результат",),
            completion_criteria=tuple(criteria),
            forbidden_substitutions=tuple(forbidden),
            clarification_required=bool(context.unresolved_questions),
        )

    def record_result(self, *, artifact_ids: list[str], action: str, validation: OutputValidation) -> None:
        context = self.get()
        if context is None:
            return
        values = {**context.__dict__}
        if artifact_ids:
            values["active_artifact_ids"] = artifact_ids
            values["primary_artifact_id"] = artifact_ids[0]
        values["last_completed_action"] = action if validation.accepted else "Результат отклонён: " + validation.code
        values["handoff_state"] = "COMPLETED" if validation.accepted else "BLOCKED"
        self.database.upsert_active_work_context(conversation_id=self.conversation_id, values=values)
        for handoff in self.handoff_service.recent(limit=10):
            if str(handoff["status"]) == "PENDING" and (not context.task_id or str(handoff["task_id"] or "") == context.task_id):
                self.database.update_work_handoff_status(str(handoff["id"]), "DELIVERED" if validation.accepted else "BLOCKED")
                break

    @staticmethod
    def _expected_output(intent: UserIntent, reference: ArtifactReference) -> str:
        if intent.intent == IntentType.FORMAT and (reference.artifact_type.upper() == "BOM" or reference.primary_artifact_id):
            return "BOM_DOCUMENT"
        if intent.intent == IntentType.CREATE and intent.artifact_query == "bom":
            return "BOM"
        if intent.intent == IntentType.REVIEW:
            return "REVIEW_REPORT"
        return intent.intent.value

    @staticmethod
    def _criteria(expected: str) -> list[str]:
        if expected == "BOM_DOCUMENT":
            return ["использовать переданный BOM", "сохранить значения компонентов", "создать документ BOM или зафиксировать проверяемый результат"]
        if expected == "BOM":
            return ["сформировать BOM с реальными позициями", "зарегистрировать BOM как артефакт"]
        return ["выполнить указанную операцию", "показать фактический результат"]

    @staticmethod
    def _from_row(row: Any) -> ActiveWorkContext:
        def decode(value: Any) -> tuple[str, ...]:
            try:
                parsed = json.loads(value or "[]")
                return tuple(str(item) for item in parsed) if isinstance(parsed, list) else ()
            except (TypeError, ValueError):
                return ()

        return ActiveWorkContext(
            conversation_id=int(row["conversation_id"]),
            thread_id=str(row["thread_id"]),
            task_id=str(row["task_id"]) if row["task_id"] else None,
            task_title=str(row["task_title"] or ""),
            task_goal=str(row["task_goal"] or ""),
            current_owner_agent_id=str(row["current_owner_agent_id"]) if row["current_owner_agent_id"] else None,
            previous_owner_agent_id=str(row["previous_owner_agent_id"]) if row["previous_owner_agent_id"] else None,
            active_artifact_ids=decode(row["active_artifact_ids"]),
            primary_artifact_id=str(row["primary_artifact_id"]) if row["primary_artifact_id"] else None,
            artifact_type=str(row["artifact_type"] or ""),
            source_agent_id=str(row["source_agent_id"]) if row["source_agent_id"] else None,
            current_operation=str(row["current_operation"] or "UNKNOWN"),
            expected_output_type=str(row["expected_output_type"] or ""),
            unresolved_questions=decode(row["unresolved_questions"]),
            last_completed_action=str(row["last_completed_action"] or ""),
            last_user_intent=str(row["last_user_intent"] or "UNKNOWN"),
            handoff_state=str(row["handoff_state"] or "NONE"),
            status=str(row["status"] or "CURRENT"),
            updated_at=str(row["updated_at"] or ""),
        )
