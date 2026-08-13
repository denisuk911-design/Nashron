from __future__ import annotations

import hashlib
from dataclasses import asdict, replace
from time import perf_counter
from typing import Protocol

from .models import (
    ActionClass,
    AgentIdentity,
    Artifact,
    BootstrapPackage,
    CandidateLesson,
    CanonicalAgentState,
    Checkpoint,
    ContextReference,
    EvaluationCase,
    EvaluationReport,
    EvidenceRecord,
    ProfessionalCapability,
    ProviderBinding,
    ProviderRequest,
    ProviderResult,
    SkillDecision,
    SkillVersion,
    StepState,
    StructuredHandoff,
    Task,
    TaskState,
    TaskStep,
    ToolResult,
    TraceEvent,
    WorkspaceReference,
    new_id,
    utc_now,
)
from .store import SQLitePrototypeStore


class ProviderUnavailable(RuntimeError):
    pass


class ProviderTimeout(RuntimeError):
    pass


class ToolExecutionFailure(RuntimeError):
    pass


class SimulatedCrash(RuntimeError):
    pass


class ProviderAdapter(Protocol):
    provider_id: str
    adapter_id: str
    model: str

    def execute(self, request: ProviderRequest) -> ProviderResult: ...


class ScriptedProvider:
    """Deterministic provider double used to prove provider-neutral continuity."""

    def __init__(
        self,
        provider_id: str,
        *,
        model: str,
        fail_after_successes: int | None = None,
        timeout_once_on_steps: set[str] | None = None,
        required_artifacts: dict[str, set[str]] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.adapter_id = f"scripted:{provider_id}"
        self.model = model
        self.fail_after_successes = fail_after_successes
        self.timeout_once_on_steps = set(timeout_once_on_steps or ())
        self.required_artifacts = required_artifacts or {}
        self.successful_calls = 0
        self.calls: list[ProviderRequest] = []

    def execute(self, request: ProviderRequest) -> ProviderResult:
        self.calls.append(request)
        if request.step.step_id in self.timeout_once_on_steps:
            self.timeout_once_on_steps.remove(request.step.step_id)
            raise ProviderTimeout(f"{self.provider_id} timed out on {request.step.step_id}")
        if self.fail_after_successes is not None and self.successful_calls >= self.fail_after_successes:
            raise ProviderUnavailable(f"{self.provider_id} is unavailable")
        missing = self.required_artifacts.get(request.step.step_id, set()).difference(
            request.artifact_ids
        )
        if missing:
            raise RuntimeError(f"missing structured artifact input: {sorted(missing)}")
        self.successful_calls += 1
        artifact = None
        if request.step.output_artifact_id:
            content = (
                f"{self.provider_id}:{request.step.step_id}:"
                f"inputs={','.join(request.artifact_ids) or 'none'}"
            )
            artifact = Artifact(
                artifact_id=request.step.output_artifact_id,
                organization_id=request.organization_id,
                task_id=request.task_id,
                artifact_type=request.step.output_artifact_type,
                logical_uri=(
                    f"workspace://tasks/{request.task_id}/artifacts/"
                    f"{request.step.output_artifact_id}"
                ),
                owner_agent_id=request.agent_id,
                version=1,
                content=content,
                content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                provenance=(
                    f"provider:{self.provider_id}",
                    f"step:{request.step.step_id}",
                    *(f"artifact:{item}" for item in request.artifact_ids),
                ),
            )
        return ProviderResult(
            summary=f"{self.provider_id} completed {request.step.step_id}",
            artifact=artifact,
            tool_intent=request.step.tool_name,
        )


class ContextAssemblerV2:
    """Selects provenance-bearing context under a deterministic token budget."""

    def __init__(self, store: SQLitePrototypeStore, token_budget: int = 600) -> None:
        self.store = store
        self.token_budget = token_budget

    def assemble(self, state: CanonicalAgentState, step: TaskStep) -> tuple[ContextReference, ...]:
        candidates = list(state.working_context)
        candidates.append(
            ContextReference(
                ref_id=state.active_task.task_id,
                kind="active_task",
                text=f"{state.active_task.goal}\n{step.instruction}",
                provenance=f"task:{state.active_task.task_id}",
                relevance=100,
                token_cost=max(1, len(state.active_task.goal + step.instruction) // 4),
            )
        )
        for artifact_id in dict.fromkeys([*state.artifact_ids, *step.required_artifact_ids]):
            artifact = self.store.get_artifact(artifact_id)
            if artifact is None:
                continue
            candidates.append(
                ContextReference(
                    ref_id=artifact.artifact_id,
                    kind="artifact",
                    text=artifact.content,
                    provenance=f"artifact:{artifact.artifact_id}@v{artifact.version}",
                    relevance=95 if artifact_id in step.required_artifact_ids else 70,
                    token_cost=max(1, len(artifact.content) // 4),
                )
            )
        selected: list[ContextReference] = []
        spent = 0
        for candidate in sorted(candidates, key=lambda item: (-item.relevance, item.ref_id)):
            if spent + candidate.token_cost > self.token_budget:
                continue
            selected.append(candidate)
            spent += candidate.token_cost
        return tuple(selected)


class DeterministicToolRunner:
    def __init__(self, store: SQLitePrototypeStore, fail_once: set[tuple[str, str]] | None = None) -> None:
        self.store = store
        self.fail_once = set(fail_once or ())

    def execute(self, effect_key: str, tool_name: str) -> ToolResult:
        attempt = self.store.record_tool_attempt(effect_key, tool_name)
        evidence_id = f"evidence-tool-{effect_key}-{attempt}"
        if (effect_key, tool_name) in self.fail_once and attempt == 1:
            raise ToolExecutionFailure(f"{tool_name} failed on attempt {attempt}")
        return ToolResult(
            tool_name=tool_name,
            ok=True,
            result=f"{tool_name} completed on attempt {attempt}",
            evidence_id=evidence_id,
        )


class AgentRuntimePrototype:
    def __init__(
        self,
        store: SQLitePrototypeStore,
        providers: list[ProviderAdapter],
        *,
        tool_runner: DeterministicToolRunner | None = None,
        token_budget: int = 600,
    ) -> None:
        self.store = store
        self.providers = {provider.provider_id: provider for provider in providers}
        self.tool_runner = tool_runner or DeterministicToolRunner(store)
        self.context_assembler = ContextAssemblerV2(store, token_budget=token_budget)

    def create_state(
        self,
        *,
        identity: AgentIdentity,
        capability: ProfessionalCapability,
        task: Task,
        provider_ids: tuple[str, ...],
        workspace_uri: str,
        working_context: list[ContextReference] | None = None,
    ) -> CanonicalAgentState:
        if not workspace_uri.startswith("workspace://"):
            raise ValueError("canonical workspace must use a logical workspace:// URI")
        if not provider_ids:
            raise ValueError("at least one provider is required")
        provider = self._provider(provider_ids[0])
        state = CanonicalAgentState(
            schema_version="2.0-prototype",
            run_id=new_id("run"),
            agent_id=identity.agent_id,
            organization_id=identity.organization_id,
            role_id=identity.role_id,
            identity=identity,
            capability=capability,
            active_task=task,
            task_state=TaskState.READY,
            task_plan=[step.step_id for step in task.steps],
            conversation_summary="",
            working_context=list(working_context or []),
            skills_used=list(capability.skill_refs),
            knowledge_used=list(capability.knowledge_refs),
            standards_used=[],
            artifact_ids=[],
            findings=[],
            decisions=[],
            tool_results=[],
            evidence=[],
            workspace=WorkspaceReference(
                workspace_id=new_id("workspace"),
                root_uri=workspace_uri,
                permissions=("read", "write", "create", "modify", "execute"),
            ),
            pending_actions=[],
            checkpoint=Checkpoint(run_id=""),
            provider_binding=ProviderBinding(
                provider_id=provider.provider_id,
                adapter_id=provider.adapter_id,
                model=provider.model,
                candidate_provider_ids=provider_ids,
            ),
            completed_effect_keys=[],
            trace_id=new_id("trace"),
        )
        state.checkpoint.run_id = state.run_id
        self.store.save_identity(identity, capability.profession_id)
        return self.store.save_state(state, "created")

    def run(
        self,
        run_id: str,
        *,
        crash_after_effect_key: str = "",
        max_completed_steps: int | None = None,
    ) -> CanonicalAgentState:
        state = self.store.load_state(run_id)
        if state.task_state == TaskState.COMPLETED:
            return state
        state.task_state = TaskState.RUNNING
        completed_this_call = 0
        while True:
            step = next(
                (item for item in state.active_task.steps if item.state != StepState.COMPLETED),
                None,
            )
            if step is None:
                state.task_state = TaskState.COMPLETED
                state.pending_actions.clear()
                return self.store.save_state(state, "task_completed")
            if max_completed_steps is not None and completed_this_call >= max_completed_steps:
                return self.store.save_state(state, "bounded_run_pause")
            if step.action_class == ActionClass.FORBIDDEN:
                state.task_state = TaskState.FAILED
                step.state = StepState.FAILED
                step.last_error = "FORBIDDEN"
                return self.store.save_state(state, "forbidden_action")
            if step.action_class == ActionClass.APPROVAL_REQUIRED:
                state.task_state = TaskState.WAITING_APPROVAL
                state.pending_actions = [step.step_id]
                return self.store.save_state(state, "approval_required")

            committed = self.store.load_effect(step.effect_key)
            if committed is not None:
                self._apply_effect(state, step, committed)
                self._trace(state, step, "EFFECT_RECONCILED", result="committed effect reused")
                self.store.save_state(state, f"reconciled:{step.step_id}")
                completed_this_call += 1
                continue

            self._validate_required_artifacts(step)
            context = self.context_assembler.assemble(state, step)
            request = ProviderRequest(
                run_id=state.run_id,
                agent_id=state.agent_id,
                organization_id=state.organization_id,
                task_id=state.active_task.task_id,
                step=step,
                context=context,
                artifact_ids=tuple(dict.fromkeys([*state.artifact_ids, *step.required_artifact_ids])),
            )
            provider = self._provider(state.provider_binding.provider_id)
            started = utc_now()
            started_clock = perf_counter()
            step.attempts += 1
            try:
                result = provider.execute(request)
            except (ProviderUnavailable, ProviderTimeout) as exc:
                step.last_error = type(exc).__name__
                event_type = (
                    "PROVIDER_TIMEOUT"
                    if isinstance(exc, ProviderTimeout)
                    else "PROVIDER_UNAVAILABLE"
                )
                self._trace(
                    state,
                    step,
                    event_type,
                    provider=provider,
                    started_at=started,
                    latency_ms=(perf_counter() - started_clock) * 1000,
                    errors=(str(exc),),
                )
                self._switch_provider(state)
                self.store.save_state(state, f"provider_switch:{step.step_id}")
                continue

            tool_result = None
            if step.tool_name:
                try:
                    tool_result = self.tool_runner.execute(step.effect_key, step.tool_name)
                except ToolExecutionFailure as exc:
                    step.last_error = str(exc)
                    state.task_state = TaskState.WAITING_RETRY
                    failed_result = ToolResult(
                        tool_name=step.tool_name,
                        ok=False,
                        result=str(exc),
                        evidence_id=f"evidence-tool-failure-{step.effect_key}",
                    )
                    state.tool_results.append(failed_result)
                    self._trace(
                        state,
                        step,
                        "TOOL_FAILURE",
                        provider=provider,
                        started_at=started,
                        latency_ms=(perf_counter() - started_clock) * 1000,
                        errors=(str(exc),),
                        tools=(step.tool_name,),
                    )
                    self.store.save_state(state, f"tool_failure:{step.step_id}")
                    raise

            effect_payload = self._effect_payload(result, tool_result)
            if not self.store.commit_effect(step.effect_key, effect_payload):
                effect_payload = self.store.load_effect(step.effect_key) or effect_payload
            if crash_after_effect_key == step.effect_key:
                raise SimulatedCrash(f"crash after committed effect {step.effect_key}")

            self._apply_effect(state, step, effect_payload)
            self._trace(
                state,
                step,
                "STEP_COMPLETED",
                provider=provider,
                started_at=started,
                latency_ms=(perf_counter() - started_clock) * 1000,
                result=result.summary,
                artifacts=((result.artifact.artifact_id,) if result.artifact else ()),
                tools=((step.tool_name,) if step.tool_name else ()),
            )
            self.store.save_state(state, f"step_completed:{step.step_id}")
            completed_this_call += 1

    def create_handoff(
        self,
        *,
        from_agent_id: str,
        to_agent_id: str,
        task_id: str,
        intent: str,
        artifact_ids: list[str],
        expected_output: str,
        acceptance: list[str],
        constraints: list[str] | None = None,
        evidence_requirements: list[str] | None = None,
    ) -> StructuredHandoff:
        missing = [item for item in artifact_ids if self.store.get_artifact(item) is None]
        if missing:
            raise KeyError(f"handoff artifacts do not exist: {missing}")
        handoff = StructuredHandoff(
            handoff_id=new_id("handoff"),
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            task_id=task_id,
            intent=intent,
            artifact_ids=artifact_ids,
            expected_output=expected_output,
            constraints=list(constraints or []),
            context_refs=[f"artifact:{item}" for item in artifact_ids],
            acceptance=acceptance,
            evidence_requirements=list(evidence_requirements or ["artifact_created"]),
        )
        self.store.save_handoff(handoff)
        return handoff

    def execute_handoff(
        self,
        handoff_id: str,
        *,
        organization_id: str,
        provider_id: str,
        output_artifact_id: str,
    ) -> Artifact:
        handoff = self.store.get_handoff(handoff_id)
        if any(self.store.get_artifact(item) is None for item in handoff.artifact_ids):
            raise KeyError("handoff input artifact is missing")
        step = TaskStep(
            step_id=f"handoff:{handoff.handoff_id}",
            instruction=handoff.intent,
            expected_output=handoff.expected_output,
            effect_key=f"effect:{handoff.handoff_id}",
            required_artifact_ids=list(handoff.artifact_ids),
            output_artifact_id=output_artifact_id,
            output_artifact_type="review",
        )
        request = ProviderRequest(
            run_id=f"handoff-run:{handoff.handoff_id}",
            agent_id=handoff.to_agent_id,
            organization_id=organization_id,
            task_id=handoff.task_id,
            step=step,
            context=tuple(
                ContextReference(
                    ref_id=item,
                    kind="artifact",
                    text=self.store.get_artifact(item).content,  # type: ignore[union-attr]
                    provenance=f"handoff:{handoff.handoff_id}/artifact:{item}",
                    relevance=100,
                    token_cost=10,
                )
                for item in handoff.artifact_ids
            ),
            artifact_ids=tuple(handoff.artifact_ids),
            handoff_id=handoff.handoff_id,
        )
        result = self._provider(provider_id).execute(request)
        if result.artifact is None:
            raise RuntimeError("handoff receiver did not create the expected artifact")
        self.store.save_artifact(result.artifact)
        handoff.status = "COMPLETED"
        self.store.save_handoff(handoff)
        return result.artifact

    def _validate_required_artifacts(self, step: TaskStep) -> None:
        missing = [item for item in step.required_artifact_ids if self.store.get_artifact(item) is None]
        if missing:
            raise KeyError(f"required artifacts are missing: {missing}")

    def _effect_payload(
        self, result: ProviderResult, tool_result: ToolResult | None
    ) -> dict[str, object]:
        return {
            "summary": result.summary,
            "artifact": asdict(result.artifact) if result.artifact else None,
            "tool_result": asdict(tool_result) if tool_result else None,
        }

    def _apply_effect(
        self, state: CanonicalAgentState, step: TaskStep, payload: dict[str, object]
    ) -> None:
        artifact_payload = payload.get("artifact")
        artifact = None
        if isinstance(artifact_payload, dict):
            artifact_payload = dict(artifact_payload)
            artifact_payload["provenance"] = tuple(artifact_payload.get("provenance", ()))
            artifact = Artifact(**artifact_payload)
            self.store.save_artifact(artifact)
            if artifact.artifact_id not in state.artifact_ids:
                state.artifact_ids.append(artifact.artifact_id)
        tool_payload = payload.get("tool_result")
        if isinstance(tool_payload, dict):
            tool_result = ToolResult(**tool_payload)
            if tool_result.evidence_id not in {item.evidence_id for item in state.tool_results}:
                state.tool_results.append(tool_result)
        evidence_id = f"evidence:{step.effect_key}"
        if evidence_id not in {item.evidence_id for item in state.evidence}:
            state.evidence.append(
                EvidenceRecord(
                    evidence_id=evidence_id,
                    claim=f"completed {step.step_id}",
                    action=step.instruction,
                    artifact_ids=((artifact.artifact_id,) if artifact else ()),
                    result=str(payload.get("summary", "completed")),
                    source=f"effect:{step.effect_key}",
                )
            )
        step.state = StepState.COMPLETED
        step.last_error = ""
        step.provider_id = state.provider_binding.provider_id
        if step.effect_key not in state.completed_effect_keys:
            state.completed_effect_keys.append(step.effect_key)
        state.task_state = TaskState.RUNNING

    def _provider(self, provider_id: str) -> ProviderAdapter:
        try:
            return self.providers[provider_id]
        except KeyError as exc:
            raise ProviderUnavailable(f"provider not registered: {provider_id}") from exc

    def _switch_provider(self, state: CanonicalAgentState) -> None:
        candidates = list(state.provider_binding.candidate_provider_ids)
        current_index = candidates.index(state.provider_binding.provider_id)
        for provider_id in candidates[current_index + 1 :]:
            if provider_id not in self.providers:
                continue
            provider = self.providers[provider_id]
            state.provider_binding = ProviderBinding(
                provider_id=provider.provider_id,
                adapter_id=provider.adapter_id,
                model=provider.model,
                candidate_provider_ids=tuple(candidates),
            )
            state.decisions.append(f"provider_switch:{candidates[current_index]}->{provider_id}")
            return
        state.task_state = TaskState.FAILED
        raise ProviderUnavailable("no provider fallback is available")

    def _trace(
        self,
        state: CanonicalAgentState,
        step: TaskStep,
        event_type: str,
        *,
        provider: ProviderAdapter | None = None,
        started_at: str | None = None,
        latency_ms: float = 0.0,
        errors: tuple[str, ...] = (),
        result: str = "",
        artifacts: tuple[str, ...] = (),
        tools: tuple[str, ...] = (),
    ) -> None:
        active_provider = provider or self.providers.get(state.provider_binding.provider_id)
        self.store.append_trace(
            TraceEvent(
                trace_id=state.trace_id,
                run_id=state.run_id,
                task_id=state.active_task.task_id,
                agent_id=state.agent_id,
                provider_id=active_provider.provider_id if active_provider else "runtime",
                model=active_provider.model if active_provider else "none",
                event_type=event_type,
                started_at=started_at or utc_now(),
                ended_at=utc_now(),
                latency_ms=latency_ms,
                context_input_ids=tuple(item.ref_id for item in state.working_context),
                skill_ids=tuple(state.skills_used),
                knowledge_ids=tuple(state.knowledge_used),
                tool_names=tools,
                artifact_ids=artifacts,
                handoff_ids=(),
                errors=errors,
                result=result,
            )
        )


class LearningEngine:
    def __init__(self, store: SQLitePrototypeStore) -> None:
        self.store = store

    def lesson_from_finding(
        self,
        *,
        organization_id: str,
        profession_id: str,
        skill_id: str,
        finding_id: str,
        content: str,
        evidence_ids: tuple[str, ...],
        contributor_id: str,
    ) -> CandidateLesson:
        if not evidence_ids:
            raise ValueError("a lesson requires evidence")
        return CandidateLesson(
            lesson_id=new_id("lesson"),
            organization_id=organization_id,
            profession_id=profession_id,
            skill_id=skill_id,
            finding_id=finding_id,
            content=content,
            evidence_ids=evidence_ids,
            contributor_id=contributor_id,
        )

    def candidate_from_lesson(
        self,
        current: SkillVersion,
        lesson: CandidateLesson,
        *,
        instructions: str,
        behaviors: dict[str, str],
    ) -> SkillVersion:
        return SkillVersion(
            skill_id=current.skill_id,
            organization_id=current.organization_id,
            profession_id=current.profession_id,
            version=current.version + 1,
            instructions=instructions,
            source_refs=[*current.source_refs, f"finding:{lesson.finding_id}"],
            examples=list(current.examples),
            tools=list(current.tools),
            limitations=list(current.limitations),
            behaviors=behaviors,
            contributors=[*current.contributors, lesson.contributor_id],
            status=SkillDecision.CANDIDATE,
        )

    def evaluate_and_decide(
        self,
        current: SkillVersion,
        candidate: SkillVersion,
        dataset: list[EvaluationCase],
    ) -> EvaluationReport:
        if not dataset:
            raise ValueError("skill evaluation requires a dataset")

        def score(version: SkillVersion) -> tuple[float, set[str]]:
            passed = {
                case.case_id
                for case in dataset
                if version.behaviors.get(case.case_id) == case.expected_output
            }
            return len(passed) / len(dataset), passed

        current_score, current_passed = score(current)
        candidate_score, candidate_passed = score(candidate)
        critical_regressions = tuple(
            case.case_id
            for case in dataset
            if case.critical
            and case.case_id in current_passed
            and case.case_id not in candidate_passed
        )
        decision = (
            SkillDecision.PROMOTED
            if candidate_score > current_score and not critical_regressions
            else SkillDecision.REJECTED
        )
        candidate.status = decision
        self.store.save_skill(candidate)
        return EvaluationReport(
            skill_id=current.skill_id,
            current_version=current.version,
            candidate_version=candidate.version,
            current_score=current_score,
            candidate_score=candidate_score,
            critical_regressions=critical_regressions,
            decision=decision,
        )


class OrganizationBootstrapService:
    def __init__(self, store: SQLitePrototypeStore) -> None:
        self.store = store

    def bootstrap(self, identity: AgentIdentity, profession_id: str) -> BootstrapPackage:
        self.store.save_identity(identity, profession_id)
        return BootstrapPackage(
            agent_id=identity.agent_id,
            profession_id=profession_id,
            organizational_knowledge=tuple(
                self.store.list_validated_knowledge(identity.organization_id, profession_id)
            ),
            active_skills=tuple(self.store.list_active_skills(identity.organization_id, profession_id)),
        )
