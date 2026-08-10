from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_directory import agent_key_from_id
from .database import Database
from .skill_service import SkillService


@dataclass(frozen=True)
class SkillProgress:
    agent_key: str
    agent_id: str
    employee_name: str
    skill_title: str
    status: str
    evidence_summary: str
    tasks_completed: int
    reviews_passed: int
    qualification: str
    last_demonstrated: str
    next_required_step: str
    confidence: str
    percent: int
    uses: int
    successful_runs: int
    verified_files: int
    updated_at: str
    basis: str


class SkillProgressService:
    """Computes skill progress from persisted app data and filesystem evidence."""

    FILE_FIELDS = ("files_read", "files_created", "files_modified", "files_deleted")

    def __init__(self, database: Database, skill_service: SkillService, workspace_root: Path) -> None:
        self.database = database
        self.skill_service = skill_service
        self.workspace_root = workspace_root

    def list_progress(self) -> list[SkillProgress]:
        skills_by_agent = self.skill_service.load()
        run_stats = self._run_stats_by_agent_skill()
        rows: list[SkillProgress] = []
        for employee in self._employees():
            agent_id = str(employee["agent_id"])
            agent_key = agent_key_from_id(agent_id)
            skills = self._merge_skills(
                skills_by_agent.get(agent_key, []),
                self._assigned_package_skills(agent_id),
            )
            if not skills:
                rows.append(
                    SkillProgress(
                        agent_key=agent_key,
                        agent_id=agent_id,
                        employee_name=str(employee["display_name"]),
                        skill_title="Навыков пока нет",
                        status="Не назначен",
                        evidence_summary="Нет сохраненного навыка и подтвержденной практики.",
                        tasks_completed=0,
                        reviews_passed=0,
                        qualification="не проводилась",
                        last_demonstrated="",
                        next_required_step="Назначить навык и выполнить проверочную задачу.",
                        confidence="низкая",
                        percent=0,
                        uses=0,
                        successful_runs=0,
                        verified_files=0,
                        updated_at="",
                        basis="Нет записи навыка в agent_skills.json.",
                    )
                )
                continue
            for skill in skills:
                title = str(skill.get("title") or "Навык")
                uses = max(0, int(skill.get("uses", 0) or 0))
                stats = run_stats.get((agent_key, self._skill_id(title)), {"successful_runs": 0, "verified_files": 0, "reviews_passed": 0, "last_demonstrated": ""})
                verified_files = int(stats["verified_files"])
                successful_runs = int(stats["successful_runs"])
                reviews_passed = int(stats["reviews_passed"])
                evidence_points = min(35, successful_runs * 7) + min(55, verified_files * 18)
                evidence_points += min(10, reviews_passed * 10)
                usage_points = min(5, uses) if evidence_points else 0
                percent = min(100, evidence_points + usage_points)
                status, next_step, confidence, qualification = self._lifecycle(successful_runs, verified_files, reviews_passed)
                evidence_summary = (
                    f"применен в задачах: {successful_runs}; файловых следов: {verified_files}; "
                    f"независимых проверок: {reviews_passed}"
                )
                package_basis = str(skill.get("package_basis") or "")
                basis = (
                    f"запись навыка: да, сама по себе процент не повышает; использований: {uses}; "
                    f"успешных запусков с этим навыком: {successful_runs}; "
                    f"проверенных файловых следов по этому навыку: {verified_files}; "
                    f"проверок: {reviews_passed}"
                )
                if package_basis:
                    basis = f"{basis}; {package_basis}"
                rows.append(
                    SkillProgress(
                        agent_key=agent_key,
                        agent_id=agent_id,
                        employee_name=str(employee["display_name"]),
                        skill_title=title,
                        status=status,
                        evidence_summary=evidence_summary,
                        tasks_completed=successful_runs,
                        reviews_passed=reviews_passed,
                        qualification=qualification,
                        last_demonstrated=str(stats["last_demonstrated"]),
                        next_required_step=next_step,
                        confidence=confidence,
                        percent=percent,
                        uses=uses,
                        successful_runs=successful_runs,
                        verified_files=verified_files,
                        updated_at=str(skill.get("updated_at") or ""),
                        basis=basis,
                    )
                )
        return sorted(rows, key=lambda item: (item.employee_name.lower(), -item.percent, item.skill_title.lower()))

    def _employees(self):
        return self.database.list_agent_profiles()

    def _assigned_package_skills(self, agent_id: str) -> list[dict[str, Any]]:
        try:
            rows = self.database.list_employee_skill_assignments(agent_id)
        except Exception:
            return []
        skills: list[dict[str, Any]] = []
        for row in rows:
            skills.append(
                {
                    "title": str(row["name"]),
                    "note": str(row["purpose"] or ""),
                    "uses": 0,
                    "updated_at": str(row["updated_at"] or ""),
                    "package_basis": (
                        f"skill package: {row['skill_id']}; "
                        f"статус пакета: {row['skill_status']}; "
                        f"состояние сотрудника: {row['state']}"
                    ),
                }
            )
        return skills

    @staticmethod
    def _merge_skills(legacy_skills: list[dict[str, Any]], package_skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for skill in [*package_skills, *legacy_skills]:
            title = str(skill.get("title") or "")
            key = SkillProgressService._skill_id(title)
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(skill)
        return result

    def _run_stats_by_agent_skill(self) -> dict[tuple[str, str], dict[str, int | str]]:
        stats: dict[tuple[str, str], dict[str, int | str]] = {}
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT agent_key, logical_role, ok, parsed_response, finished_at
                FROM agent_runs
                WHERE cancelled = 0
                """
            ).fetchall()
        for row in rows:
            agent_key = str(row["agent_key"])
            skill_ids = self._skills_from_response(row["parsed_response"])
            if not skill_ids:
                continue
            role = str(row["logical_role"] or "")
            for skill_id in skill_ids:
                item = stats.setdefault(
                    (agent_key, skill_id),
                    {"successful_runs": 0, "verified_files": 0, "reviews_passed": 0, "last_demonstrated": ""},
                )
                if int(row["ok"] or 0):
                    item["successful_runs"] = int(item["successful_runs"]) + 1
                    item["last_demonstrated"] = str(row["finished_at"] or "")
                item["verified_files"] = int(item["verified_files"]) + self._verified_files_from_response(row["parsed_response"])
                if role in {"QA_ENGINEER", "VERIFICATION_ENGINEER"} and int(row["ok"] or 0):
                    item["reviews_passed"] = int(item["reviews_passed"]) + 1
        with self.database.connect() as conn:
            usage_rows = conn.execute(
                """
                SELECT ar.agent_key, ar.ok, ar.logical_role, ar.parsed_response, ar.finished_at, su.skill_id
                FROM skill_usage su
                JOIN agent_runs ar ON ar.id = su.run_id
                WHERE ar.cancelled = 0
                """
            ).fetchall()
        for row in usage_rows:
            agent_key = str(row["agent_key"])
            skill_id = self._skill_id(str(row["skill_id"]))
            if int(row["ok"] or 0):
                item = stats.setdefault(
                    (agent_key, skill_id),
                    {"successful_runs": 0, "verified_files": 0, "reviews_passed": 0, "last_demonstrated": ""},
                )
                item["successful_runs"] = int(item["successful_runs"]) + 1
                item["last_demonstrated"] = str(row["finished_at"] or "")
                item["verified_files"] = int(item["verified_files"]) + self._verified_files_from_response(row["parsed_response"])
                if str(row["logical_role"] or "") in {"QA_ENGINEER", "VERIFICATION_ENGINEER"}:
                    item["reviews_passed"] = int(item["reviews_passed"]) + 1
        return stats

    def _skills_from_response(self, raw: str | None) -> list[str]:
        if not raw:
            return []
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(payload, dict):
            return []
        values = payload.get("skills_used") or payload.get("skill_usage") or payload.get("skills")
        if not isinstance(values, list):
            return []
        result: list[str] = []
        for value in values:
            if isinstance(value, dict):
                value = value.get("skill_id") or value.get("title") or value.get("name")
            if isinstance(value, str) and value.strip():
                result.append(self._skill_id(value))
        return result

    def _verified_files_from_response(self, raw: str | None) -> int:
        if not raw:
            return 0
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return 0
        if not isinstance(payload, dict):
            return 0
        seen: set[Path] = set()
        for field in self.FILE_FIELDS:
            values = payload.get(field)
            if not isinstance(values, list):
                continue
            for value in values:
                path = self._path_from_value(value)
                if path is not None and path.exists():
                    seen.add(path)
        return len(seen)

    def _path_from_value(self, value: Any) -> Path | None:
        if isinstance(value, dict):
            value = value.get("path") or value.get("file") or value.get("relative_path")
        if not isinstance(value, str) or not value.strip():
            return None
        raw_path = Path(value.strip().strip("\"'"))
        if not raw_path.is_absolute():
            raw_path = self.workspace_root / raw_path
        try:
            resolved = raw_path.expanduser().resolve(strict=False)
            workspace = self.workspace_root.expanduser().resolve(strict=False)
        except OSError:
            return None
        if resolved != workspace and workspace not in resolved.parents:
            return None
        return resolved

    @staticmethod
    def _skill_id(title: str) -> str:
        return " ".join(title.lower().strip().split())

    @staticmethod
    def _lifecycle(successful_runs: int, verified_files: int, reviews_passed: int) -> tuple[str, str, str, str]:
        if successful_runs <= 0 and verified_files <= 0:
            return (
                "Назначен",
                "Применить навык в реальной задаче и сохранить evidence.",
                "низкая",
                "не проводилась",
            )
        if reviews_passed >= 1 and successful_runs >= 3 and verified_files >= 2:
            return ("Квалифицирован", "Поддерживать практикой и периодическим ревью.", "высокая", "пройдена")
        if reviews_passed >= 1:
            return ("Проверен", "Выполнить еще задачи с артефактами для квалификации.", "средняя", "частичная")
        if verified_files >= 1:
            return ("Показал результат", "Передать результат на независимое ревью.", "средняя", "не проводилась")
        return ("Практиковал", "Создать или привязать артефакт результата.", "низкая", "не проводилась")
