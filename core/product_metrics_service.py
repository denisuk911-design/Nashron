from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .database import Database
from .skill_progress_service import SkillProgressService


@dataclass(frozen=True)
class ProductMetric:
    name: str
    value: str
    status: str
    detail: str


@dataclass(frozen=True)
class RoutingDiagnostic:
    created_at: str
    participation_mode: str
    selected: str
    excluded: str
    reason: str
    router_version: str


@dataclass(frozen=True)
class ThreadDiagnostic:
    updated_at: str
    thread_id: str
    owner: str
    active_task_id: str
    topic: str
    expected_next_actor: str


@dataclass(frozen=True)
class QuestionDiagnostic:
    question_id: str
    updated_at: str
    status: str
    assigned: str
    question: str
    answer_message_id: str
    answered_by: str


@dataclass(frozen=True)
class SendPipelineDiagnostic:
    created_at: str
    trace_id: str
    bubble_ms: str
    event_loop_ms: str
    persisted_ms: str
    routing_ms: str
    provider_ms: str
    rendered_ms: str
    budget: str


class ProductMetricsService:
    """Local, evidence-based product metrics for the owner console."""

    def __init__(self, database: Database, skill_progress_service: SkillProgressService | None = None) -> None:
        self.database = database
        self.skill_progress_service = skill_progress_service

    def metrics(self) -> list[ProductMetric]:
        routing = self._routing_counts()
        events = self._event_counts()
        runs = self._run_counts()
        skill_counts = self._skill_counts()
        knowledge_counts = self._knowledge_counts()
        standard_counts = self._standard_counts()
        finding_counts = self._finding_counts()
        artifact_counts = self._artifact_counts()
        question_counts = self._question_counts()
        total_routes = max(1, routing["total"])
        total_runs = max(1, runs["total"])
        one_responder_rate = int(round(routing["single"] * 100 / total_routes)) if routing["total"] else 0
        direct_delivery_rate = int(round(routing["explicit_delivered"] * 100 / max(1, routing["explicit"]))) if routing["explicit"] else 0
        handoff_rate = int(round(events["handoff_started"] * 100 / max(1, events["handoff_scheduled"]))) if events["handoff_scheduled"] else 0
        unsupported_claim_rate = int(round(events["unsupported_claim"] * 100 / total_runs)) if runs["total"] else 0
        evidence_rate = int(round(runs["evidence_backed"] * 100 / total_runs)) if runs["total"] else 0
        duplicate_rate = int(round(events["duplicates"] * 100 / total_routes)) if routing["total"] else 0
        return [
            ProductMetric(
                "Точность одиночной маршрутизации",
                f"{one_responder_rate}%",
                self._status_high_good(one_responder_rate, good=80, warn=60),
                f"Один ответчик: {routing['single']} из {routing['total']} решений. Без ответа: {routing['silent']}.",
            ),
            ProductMetric(
                "Лишние ответчики",
                str(routing["extra"]),
                self._status_low_good(routing["extra"], good=0, warn=2),
                "Случаи, где выбрано больше одного сотрудника вне командного обсуждения или ревью.",
            ),
            ProductMetric(
                "Доставка прямых обращений",
                f"{direct_delivery_rate}%",
                self._status_high_good(direct_delivery_rate, good=95, warn=80),
                f"Явные адресные сообщения доставлены: {routing['explicit_delivered']} / {routing['explicit']}; промахов: {routing['explicit_missed']}.",
            ),
            ProductMetric(
                "Доставка handoff",
                f"{handoff_rate}%",
                self._status_high_good(handoff_rate, good=90, warn=70),
                f"Запланированные handoff запущены: {events['handoff_started']} / {events['handoff_scheduled']}.",
            ),
            ProductMetric(
                "Дубли и повторные ответы",
                f"{duplicate_rate}%",
                self._status_low_good(duplicate_rate, good=5, warn=15),
                f"События подавления дублей/повторов: {events['duplicates']}.",
            ),
            ProductMetric(
                "Открытые вопросы",
                str(question_counts["open"]),
                self._status_low_good(question_counts["open"], good=0, warn=3),
                f"Зафиксировано: {question_counts['total']}; ожидают принятия: {question_counts['answered']}; принято владельцем: {question_counts['accepted']}.",
            ),
            ProductMetric(
                "Попытки писать за коллег",
                str(events["impersonation"]),
                self._status_low_good(events["impersonation"], good=0, warn=2),
                "Сколько раз приложение отклонило multi-speaker ответ одного provider.",
            ),
            ProductMetric(
                "Неподтвержденные заявления",
                f"{unsupported_claim_rate}%",
                self._status_low_good(unsupported_claim_rate, good=5, warn=20),
                f"Предупреждений: {events['unsupported_claim']}; запусков: {runs['total']}.",
            ),
            ProductMetric(
                "Запуски с evidence",
                f"{evidence_rate}%",
                self._status_high_good(evidence_rate, good=60, warn=30),
                f"Запусков с файлами/checks/evidence: {runs['evidence_backed']} из {runs['total']}.",
            ),
            ProductMetric(
                "Артефакты подтверждены",
                f"{artifact_counts['verified']} / {artifact_counts['total']}",
                self._status_low_good(artifact_counts["missing"] + artifact_counts["unsafe"], good=0, warn=2),
                f"OBSERVED: {artifact_counts['observed']}; MISSING: {artifact_counts['missing']}; DELETED: {artifact_counts['deleted']}; unsafe: {artifact_counts['unsafe']}.",
            ),
            ProductMetric(
                "Отмененные запуски",
                str(runs["cancelled"]),
                self._status_low_good(runs["cancelled"], good=0, warn=3),
                "Отмены должны быть видны и не считаться успешной работой.",
            ),
            ProductMetric(
                "Долгие ответы",
                str(events["latency_warnings"]),
                self._status_low_good(events["latency_warnings"], good=0, warn=5),
                f"Предупреждений ожидания: {events['latency_warnings']}; автоостановок: {events['latency_timeouts']}.",
            ),
            ProductMetric(
                "Навыки с evidence",
                str(skill_counts["with_evidence"]),
                "OK" if skill_counts["with_evidence"] else "WATCH",
                f"Всего навыков в витрине: {skill_counts['total']}; квалифицировано: {skill_counts['qualified']}.",
            ),
            ProductMetric(
                "Карточки знаний использованы",
                str(knowledge_counts["applied"]),
                "OK" if knowledge_counts["applied"] else "WATCH",
                f"Активных карточек: {knowledge_counts['active']}; всего: {knowledge_counts['total']}; SUPPLIED: {knowledge_counts['supplied']}; APPLIED: {knowledge_counts['applied']}; IGNORED: {knowledge_counts['ignored']}; MISAPPLIED: {knowledge_counts['misapplied']}.",
            ),
            ProductMetric(
                "Стандарты использованы",
                str(standard_counts["applied"]),
                "OK" if standard_counts["applied"] else "WATCH",
                f"Активных стандартов: {standard_counts['active']}; всего: {standard_counts['total']}; SUPPLIED: {standard_counts['supplied']}; APPLIED: {standard_counts['applied']}; IGNORED: {standard_counts['ignored']}; MISAPPLIED: {standard_counts['misapplied']}.",
            ),
            ProductMetric(
                "Открытые QA findings",
                str(finding_counts["open"]),
                self._status_low_good(finding_counts["blocking"], good=0, warn=2),
                f"Всего findings: {finding_counts['total']}; blocking HIGH/CRITICAL: {finding_counts['blocking']}; повторов: {finding_counts['repeated']}.",
            ),
        ]

    def recent_send_pipeline_diagnostics(self, limit: int = 30) -> list[SendPipelineDiagnostic]:
        with self.database.connect() as conn:
            rows = conn.execute(
                "SELECT created_at, detail FROM app_events WHERE event_type = 'send_pipeline_trace' ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        diagnostics: list[SendPipelineDiagnostic] = []
        seen: set[str] = set()
        for row in rows:
            try:
                payload = json.loads(str(row["detail"] or "{}"))
            except json.JSONDecodeError:
                continue
            trace_id = str(payload.get("trace_id") or "")
            if not trace_id or trace_id in seen:
                continue
            seen.add(trace_id)
            stages = payload.get("stages_ms") if isinstance(payload.get("stages_ms"), dict) else {}
            provider_values = [
                float(value)
                for key, value in stages.items()
                if str(key).startswith("provider_started")
                or (str(key).startswith("provider_") and str(key).endswith("_started"))
            ]
            rendered_values = [float(value) for key, value in stages.items() if str(key).startswith("response_rendered")]
            diagnostics.append(
                SendPipelineDiagnostic(
                    created_at=str(row["created_at"]),
                    trace_id=trace_id,
                    bubble_ms=self._ms(stages.get("user_bubble_created", stages.get("bubble_created"))),
                    event_loop_ms=self._ms(stages.get("event_loop_returned")),
                    persisted_ms=self._ms(stages.get("message_persisted", stages.get("persisted"))),
                    routing_ms=self._ms(stages.get("routing_completed", stages.get("routing_finished"))),
                    provider_ms=self._ms(min(provider_values) if provider_values else None),
                    rendered_ms=self._ms(max(rendered_values) if rendered_values else None),
                    budget="OK" if bool(payload.get("bubble_budget_ok")) else "SLOW",
                )
            )
        return diagnostics

    @staticmethod
    def _ms(value) -> str:
        try:
            return f"{float(value):.1f}"
        except (TypeError, ValueError):
            return "-"

    def recent_routing_diagnostics(self, limit: int = 20) -> list[RoutingDiagnostic]:
        diagnostics: list[RoutingDiagnostic] = []
        for row in self.database.list_routing_decisions(limit):
            selected = self._json_list(row["selected_responders"])
            excluded = self._json_dict(row["excluded_responders"])
            diagnostics.append(
                RoutingDiagnostic(
                    created_at=str(row["created_at"]),
                    participation_mode=str(row["participation_mode"]),
                    selected=", ".join(selected) or "никто",
                    excluded=", ".join(f"{key}: {value}" for key, value in excluded.items()) or "нет",
                    reason=str(row["reason"]),
                    router_version=str(row["router_version"]),
                )
            )
        return diagnostics

    def recent_thread_diagnostics(self, limit: int = 10) -> list[ThreadDiagnostic]:
        result: list[ThreadDiagnostic] = []
        for row in self.database.list_conversation_threads(limit):
            result.append(
                ThreadDiagnostic(
                    updated_at=str(row["updated_at"]),
                    thread_id=str(row["id"]),
                    owner=str(row["active_addressee_agent_id"] or "нет"),
                    active_task_id=str(row["active_task_id"] or "нет"),
                    topic=str(row["active_topic"] or "нет"),
                    expected_next_actor=str(row["expected_next_actor"] or "нет"),
                )
            )
        return result

    def recent_question_diagnostics(self, limit: int = 20) -> list[QuestionDiagnostic]:
        result: list[QuestionDiagnostic] = []
        for row in self.database.list_thread_questions(limit=limit):
            assigned = self._json_list(row["assigned_agent_keys"])
            result.append(
                QuestionDiagnostic(
                    question_id=str(row["id"]),
                    updated_at=str(row["updated_at"]),
                    status=str(row["status"]),
                    assigned=", ".join(assigned) or "не назначен",
                    question=str(row["question_text"]),
                    answer_message_id=str(row["answer_message_id"] or "нет"),
                    answered_by=str(row["answered_by_agent_key"] or "нет"),
                )
            )
        return result

    def accept_question_answer(self, question_id: str) -> bool:
        updated = self.database.update_thread_question_status(question_id, "ACCEPTED")
        if updated:
            self.database.log_event("thread_question_answer_accepted", question_id)
        return updated

    def reopen_question(self, question_id: str) -> bool:
        updated = self.database.update_thread_question_status(question_id, "OPEN")
        if updated:
            self.database.log_event("thread_question_reopened", question_id)
        return updated

    def _routing_counts(self) -> dict[str, int]:
        counts = {"total": 0, "single": 0, "silent": 0, "extra": 0, "explicit": 0, "explicit_delivered": 0, "explicit_missed": 0}
        for row in self.database.list_routing_decisions():
            counts["total"] += 1
            explicit = self._json_list(row["explicit_recipients"])
            selected = self._json_list(row["selected_responders"])
            mode = str(row["participation_mode"])
            if explicit:
                counts["explicit"] += 1
                if set(explicit).issubset(set(selected)) and selected:
                    counts["explicit_delivered"] += 1
                else:
                    counts["explicit_missed"] += 1
            if len(selected) == 1:
                counts["single"] += 1
            elif not selected:
                counts["silent"] += 1
            elif mode not in {"TEAM_DISCUSSION", "REVIEW_REQUEST"}:
                counts["extra"] += 1
        return counts

    def _event_counts(self) -> dict[str, int]:
        counts = {
            "duplicates": 0,
            "impersonation": 0,
            "unsupported_claim": 0,
            "latency_warnings": 0,
            "latency_timeouts": 0,
            "handoff_scheduled": 0,
            "handoff_started": 0,
        }
        with self.database.connect() as conn:
            rows = conn.execute("SELECT event_type FROM app_events").fetchall()
        for row in rows:
            event_type = str(row["event_type"])
            if "duplicate" in event_type or "repeated_content" in event_type:
                counts["duplicates"] += 1
            if "impersonated" in event_type:
                counts["impersonation"] += 1
            if event_type == "unsupported_claim_warning":
                counts["unsupported_claim"] += 1
            if event_type in {"response_latency_soft_warning", "response_latency_extended_warning"}:
                counts["latency_warnings"] += 1
            if event_type == "response_latency_timeout_cancelled":
                counts["latency_timeouts"] += 1
            if event_type == "contextual_handoff_scheduled":
                counts["handoff_scheduled"] += 1
            if event_type == "contextual_handoff_started":
                counts["handoff_started"] += 1
        return counts

    def _run_counts(self) -> dict[str, int]:
        counts = {"total": 0, "cancelled": 0, "evidence_backed": 0}
        with self.database.connect() as conn:
            rows = conn.execute("SELECT cancelled, parsed_response FROM agent_runs").fetchall()
        for row in rows:
            counts["total"] += 1
            if int(row["cancelled"] or 0):
                counts["cancelled"] += 1
            if self._has_evidence(row["parsed_response"]):
                counts["evidence_backed"] += 1
        return counts

    def _question_counts(self) -> dict[str, int]:
        counts = {"total": 0, "open": 0, "answered": 0, "accepted": 0}
        with self.database.connect() as conn:
            rows = conn.execute("SELECT status FROM thread_questions").fetchall()
        for row in rows:
            counts["total"] += 1
            status = str(row["status"])
            if status == "OPEN":
                counts["open"] += 1
            elif status == "ANSWERED":
                counts["answered"] += 1
            elif status == "ACCEPTED":
                counts["accepted"] += 1
        return counts

    def _skill_counts(self) -> dict[str, int]:
        counts = {"total": 0, "with_evidence": 0, "qualified": 0}
        if self.skill_progress_service is None:
            return counts
        for row in self.skill_progress_service.list_progress():
            if row.skill_title == "Навыков пока нет":
                continue
            counts["total"] += 1
            if row.tasks_completed or row.verified_files or row.reviews_passed:
                counts["with_evidence"] += 1
            if row.status == "Квалифицирован":
                counts["qualified"] += 1
        return counts

    def _knowledge_counts(self) -> dict[str, int]:
        counts = {
            "total": 0,
            "active": 0,
            "used": 0,
            "usage_events": 0,
            "supplied": 0,
            "applied": 0,
            "ignored": 0,
            "misapplied": 0,
        }
        with self.database.connect() as conn:
            rows = conn.execute("SELECT id, status FROM knowledge_cards").fetchall()
            usage_rows = conn.execute("SELECT knowledge_id, usage_type FROM knowledge_usage").fetchall()
        used_ids = {str(row["knowledge_id"]) for row in usage_rows if str(row["usage_type"]) == "SUPPLIED"}
        applied_ids: set[str] = set()
        counts["usage_events"] = len(usage_rows)
        counts["used"] = len(used_ids)
        for row in rows:
            counts["total"] += 1
            if str(row["status"]) == "ACTIVE":
                counts["active"] += 1
        for row in usage_rows:
            usage_type = str(row["usage_type"])
            if usage_type == "SUPPLIED":
                counts["supplied"] += 1
            elif usage_type == "APPLIED":
                applied_ids.add(str(row["knowledge_id"]))
            elif usage_type == "IGNORED":
                counts["ignored"] += 1
            elif usage_type == "MISAPPLIED":
                counts["misapplied"] += 1
        counts["applied"] = len(applied_ids)
        return counts

    def _standard_counts(self) -> dict[str, int]:
        counts = {
            "total": 0,
            "active": 0,
            "used": 0,
            "usage_events": 0,
            "supplied": 0,
            "applied": 0,
            "ignored": 0,
            "misapplied": 0,
        }
        with self.database.connect() as conn:
            rows = conn.execute("SELECT id, status FROM standard_cards").fetchall()
            usage_rows = conn.execute("SELECT standard_id, usage_type FROM standard_usage").fetchall()
        used_ids = {str(row["standard_id"]) for row in usage_rows if str(row["usage_type"]) == "SUPPLIED"}
        applied_ids: set[str] = set()
        counts["usage_events"] = len(usage_rows)
        counts["used"] = len(used_ids)
        for row in rows:
            counts["total"] += 1
            if str(row["status"]) == "ACTIVE":
                counts["active"] += 1
        for row in usage_rows:
            usage_type = str(row["usage_type"])
            if usage_type == "SUPPLIED":
                counts["supplied"] += 1
            elif usage_type == "APPLIED":
                applied_ids.add(str(row["standard_id"]))
            elif usage_type == "IGNORED":
                counts["ignored"] += 1
            elif usage_type == "MISAPPLIED":
                counts["misapplied"] += 1
        counts["applied"] = len(applied_ids)
        return counts

    def _finding_counts(self) -> dict[str, int]:
        counts = {"total": 0, "open": 0, "blocking": 0, "repeated": 0}
        closed = {"RESOLVED", "ACCEPTED_RISK", "REJECTED", "DEFERRED"}
        repeat_keys: dict[str, int] = {}
        with self.database.connect() as conn:
            rows = conn.execute("SELECT severity, status, repeat_key FROM findings").fetchall()
        for row in rows:
            counts["total"] += 1
            status = str(row["status"])
            severity = str(row["severity"])
            repeat_key = str(row["repeat_key"] or "")
            if status not in closed:
                counts["open"] += 1
                if severity in {"HIGH", "CRITICAL"}:
                    counts["blocking"] += 1
            if repeat_key:
                repeat_keys[repeat_key] = repeat_keys.get(repeat_key, 0) + 1
        counts["repeated"] = sum(1 for value in repeat_keys.values() if value > 1)
        return counts

    def _artifact_counts(self) -> dict[str, int]:
        counts = {"total": 0, "observed": 0, "verified": 0, "missing": 0, "deleted": 0, "unsafe": 0}
        with self.database.connect() as conn:
            rows = conn.execute("SELECT status, validation_status FROM artifacts").fetchall()
        for row in rows:
            counts["total"] += 1
            status = str(row["status"])
            validation_status = str(row["validation_status"])
            if status == "OBSERVED":
                counts["observed"] += 1
            if status == "MISSING":
                counts["missing"] += 1
            if status == "DELETED":
                counts["deleted"] += 1
            if validation_status in {"VERIFIED", "VERIFIED_ABSENT"}:
                counts["verified"] += 1
            if validation_status == "UNSAFE_PATH":
                counts["unsafe"] += 1
        return counts

    def _has_evidence(self, raw: str | None) -> bool:
        if not raw:
            return False
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        for field in ("evidence", "files_read", "files_created", "files_modified", "files_deleted", "checks"):
            value = payload.get(field)
            if isinstance(value, list) and any(value):
                return True
        return False

    @staticmethod
    def _json_list(value: Any) -> list[str]:
        try:
            payload = json.loads(str(value or "[]"))
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        return [str(item) for item in payload]

    @staticmethod
    def _json_dict(value: Any) -> dict[str, str]:
        try:
            payload = json.loads(str(value or "{}"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        return {str(key): str(item) for key, item in payload.items()}

    @staticmethod
    def _status_high_good(value: int, *, good: int, warn: int) -> str:
        if value >= good:
            return "OK"
        if value >= warn:
            return "WATCH"
        return "RISK"

    @staticmethod
    def _status_low_good(value: int, *, good: int, warn: int) -> str:
        if value <= good:
            return "OK"
        if value <= warn:
            return "WATCH"
        return "RISK"
