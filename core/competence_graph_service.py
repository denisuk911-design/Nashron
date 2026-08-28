from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .database import Database


@dataclass(frozen=True)
class OrganizationMemory:
    entry_id: str
    organization_id: str
    title: str
    content: str
    lifecycle_state: str
    source_agent_id: str | None
    source_employee_name: str
    source_run_id: str | None
    review_run_id: str | None
    evidence: dict[str, Any]


@dataclass(frozen=True)
class CompetenceNode:
    node_id: str
    organization_id: str
    agent_id: str | None
    employee_name: str
    competence: str
    growth_points: int
    lifecycle_state: str
    source_memory_id: str | None
    evidence: dict[str, Any]


class CompetenceGraphService:
    """Turns only reviewed, persisted work into organization knowledge and competence."""

    REVIEW_ROLES = {"QA_ENGINEER", "VERIFICATION_ENGINEER", "REVIEWER"}
    PROMOTABLE_OUTCOMES = {"PASS", "REWORK"}

    def __init__(self, database: Database) -> None:
        self.database = database

    def propose_knowledge(
        self,
        *,
        organization_id: str,
        source_run_id: str,
        competence: str,
        title: str,
        content: str,
        outcome: str = "PASS",
    ) -> OrganizationMemory:
        outcome = outcome.upper().strip()
        if outcome not in self.PROMOTABLE_OUTCOMES:
            raise ValueError("evidence_pass_or_rework_required")
        run, evidence = self._verified_work_evidence(source_run_id)
        agent_id = str(run["agent_id"] or "")
        profile = self.database.get_agent_profile(agent_id)
        if profile is None:
            raise ValueError("source_employee_missing")
        entry_id = self.database.create_organization_memory_entry(
            {
                "organization_id": organization_id,
                "kind": "KNOWLEDGE",
                "title": " ".join(title.split()),
                "content": content.strip(),
                "source_agent_id": agent_id,
                "source_employee_name": str(profile["display_name"] or ""),
                "source_run_id": source_run_id,
                "evidence": {"competence": competence.strip(), "outcome": outcome, **evidence},
            }
        )
        return self._memory(entry_id)

    def verify_knowledge(self, entry_id: str, review_run_id: str) -> tuple[OrganizationMemory, CompetenceNode]:
        entry = self.database.get_organization_memory_entry(entry_id)
        if entry is None:
            raise ValueError("unknown_organization_memory")
        if str(entry["lifecycle_state"]) != "CANDIDATE":
            raise ValueError("knowledge_not_candidate")
        review = self._accepted_independent_review(entry, review_run_id)
        evidence = Database.loads(str(entry["evidence"] or "{}"), {})
        if not isinstance(evidence, dict):
            evidence = {}
        verified_evidence = {**evidence, "review_run_id": review_run_id, "review_checks": review["checks"]}
        self.database.verify_organization_memory_entry(entry_id, review_run_id, verified_evidence)
        competence = str(evidence.get("competence") or "").strip()
        if not competence:
            raise ValueError("competence_required")
        node_id = self.database.upsert_organization_competence_node(
            {
                "organization_id": str(entry["organization_id"]),
                "agent_id": entry["source_agent_id"],
                "employee_name": str(entry["source_employee_name"] or ""),
                "competence": competence,
                "source_memory_id": entry_id,
                "evidence": verified_evidence,
            }
        )
        return self._memory(entry_id), self._node(node_id, str(entry["organization_id"]))

    def list_memory(self, organization_id: str, lifecycle_state: str | None = None) -> list[OrganizationMemory]:
        return [self._memory_row(row) for row in self.database.list_organization_memory_entries(organization_id, lifecycle_state)]

    def list_competence(self, organization_id: str, agent_id: str | None = None) -> list[CompetenceNode]:
        return [self._node_row(row) for row in self.database.list_organization_competence_nodes(organization_id, agent_id)]

    def _verified_work_evidence(self, run_id: str):
        run = self.database.get_agent_run(run_id)
        if run is None or not int(run["ok"] or 0) or int(run["cancelled"] or 0):
            raise ValueError("successful_source_run_required")
        with self.database.connect() as conn:
            artifact_ids = [str(row["id"]) for row in conn.execute(
                "SELECT id FROM artifacts WHERE created_by_run_id = ? AND deleted = 0", (run_id,)
            ).fetchall()]
            tool_ids = [str(row["id"]) for row in conn.execute(
                "SELECT id FROM tool_evidence WHERE run_id = ?", (run_id,)
            ).fetchall()]
        if not artifact_ids and not tool_ids:
            raise ValueError("work_evidence_required")
        return run, {"artifact_ids": artifact_ids, "tool_evidence_ids": tool_ids}

    def _accepted_independent_review(self, entry, review_run_id: str) -> dict[str, Any]:
        run = self.database.get_agent_run(review_run_id)
        if run is None or not int(run["ok"] or 0) or int(run["cancelled"] or 0):
            raise ValueError("successful_review_run_required")
        if str(run["agent_id"] or "") == str(entry["source_agent_id"] or ""):
            raise ValueError("independent_reviewer_required")
        if str(run["logical_role"] or "") not in self.REVIEW_ROLES:
            raise ValueError("qualified_reviewer_role_required")
        payload = Database.loads(str(run["parsed_response"] or "{}"), {})
        checks = payload.get("checks", []) if isinstance(payload, dict) else []
        findings = payload.get("findings", []) if isinstance(payload, dict) else []
        blocking = any(
            isinstance(item, dict) and (bool(item.get("blocking")) or str(item.get("severity", "")).upper() in {"BLOCKER", "CRITICAL", "HIGH"})
            for item in findings
        )
        if not checks or blocking:
            raise ValueError("accepted_review_evidence_required")
        return {"checks": checks}

    def _memory(self, entry_id: str) -> OrganizationMemory:
        row = self.database.get_organization_memory_entry(entry_id)
        if row is None:
            raise ValueError("unknown_organization_memory")
        return self._memory_row(row)

    def _node(self, node_id: str, organization_id: str) -> CompetenceNode:
        return next(node for node in self.list_competence(organization_id) if node.node_id == node_id)

    @staticmethod
    def _memory_row(row) -> OrganizationMemory:
        return OrganizationMemory(
            str(row["id"]), str(row["organization_id"]), str(row["title"]), str(row["content"] or ""),
            str(row["lifecycle_state"]), str(row["source_agent_id"]) if row["source_agent_id"] else None,
            str(row["source_employee_name"] or ""), str(row["source_run_id"]) if row["source_run_id"] else None,
            str(row["review_run_id"]) if row["review_run_id"] else None,
            Database.loads(str(row["evidence"] or "{}"), {}),
        )

    @staticmethod
    def _node_row(row) -> CompetenceNode:
        return CompetenceNode(
            str(row["id"]), str(row["organization_id"]), str(row["agent_id"]) if row["agent_id"] else None,
            str(row["employee_name"] or ""), str(row["competence"]), int(row["growth_points"] or 0),
            str(row["lifecycle_state"]), str(row["source_memory_id"]) if row["source_memory_id"] else None,
            Database.loads(str(row["evidence"] or "{}"), {}),
        )
