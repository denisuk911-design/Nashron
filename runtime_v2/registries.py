from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import Artifact, ArtifactRevision, Finding, FindingStatus, WorkflowState, new_id


class StateArtifactRegistry:
    def add_revision(
        self,
        state: WorkflowState,
        artifact_data: dict[str, Any],
        *,
        employee_id: str,
        provider_id: str,
    ) -> str:
        artifact_id = str(artifact_data.get("artifact_id") or new_id("artifact"))
        artifact = state.artifacts.get(artifact_id)
        if artifact is None:
            artifact = Artifact(
                artifact_id=artifact_id,
                task_id=state.task_id,
                artifact_type=str(artifact_data.get("artifact_type") or "DOCUMENT"),
            )
            state.artifacts[artifact_id] = artifact
        evidence = dict(artifact_data.get("evidence") or {})
        content = artifact_data.get("content", "")
        digest = str(artifact_data.get("content_hash") or hashlib.sha256(
            json.dumps(content, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest())
        artifact.revisions.append(
            ArtifactRevision(
                revision=artifact.current_revision + 1,
                producer_employee_id=employee_id,
                provider_id=provider_id,
                content_hash=digest,
                evidence=evidence,
            )
        )
        return artifact_id


class StateFindingRegistry:
    _transitions = {
        FindingStatus.OPEN: {FindingStatus.ASSIGNED, FindingStatus.CLOSED},
        FindingStatus.ASSIGNED: {FindingStatus.RESOLVED, FindingStatus.REOPENED},
        FindingStatus.RESOLVED: {FindingStatus.CLOSED, FindingStatus.REOPENED},
        FindingStatus.REOPENED: {FindingStatus.ASSIGNED, FindingStatus.RESOLVED},
        FindingStatus.CLOSED: {FindingStatus.REOPENED},
    }

    def add(self, state: WorkflowState, finding_data: dict[str, Any]) -> str:
        artifact_id = str(finding_data["artifact_id"])
        if artifact_id not in state.artifacts:
            raise ValueError("finding_artifact_missing")
        revision = int(finding_data.get("revision") or state.artifacts[artifact_id].current_revision)
        finding_id = str(finding_data.get("finding_id") or new_id("finding"))
        state.findings[finding_id] = Finding(
            finding_id=finding_id,
            artifact_id=artifact_id,
            revision=revision,
            severity=str(finding_data.get("severity") or "MEDIUM"),
            description=str(finding_data.get("description") or ""),
            evidence=dict(finding_data.get("evidence") or {}),
            owner_employee_id=str(finding_data.get("owner_employee_id") or ""),
        )
        return finding_id

    def transition(self, state: WorkflowState, finding_id: str, status: str) -> None:
        finding = state.findings[finding_id]
        target = FindingStatus(status)
        if target not in self._transitions[finding.status]:
            raise ValueError(f"invalid_finding_transition:{finding.status}:{target}")
        finding.status = target
