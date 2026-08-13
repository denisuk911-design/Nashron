from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from .checkpoint_store import JsonCheckpointStore
from .engine import PrototypeWorkflowEngine
from .models import ActionRisk, WorkflowDefinition, WorkflowStatus, WorkflowStep
from .provider import LocalAgentRuntime, ScriptedProviderAdapter
from .trace import LocalTraceService


@dataclass
class BenchmarkMetrics:
    engine: str
    status: str
    agent_calls: int
    handoffs: int
    duplicate_work: int
    lost_context: int
    manual_prompt_glue: int
    recovery_supported: bool
    duration_ms: float
    artifact_count: int
    trace_events: int


def expense_app_definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        name="expense-app-concept-v1",
        steps=[
            WorkflowStep("director-plan", "director", "PLAN", "PROJECT_PLAN"),
            WorkflowStep("product", "product-specialist", "PRODUCT_CONCEPT", "PRODUCT_CONCEPT", ["director-plan"]),
            WorkflowStep(
                "technical",
                "technical-specialist",
                "TECHNICAL_CONCEPT",
                "TECHNICAL_CONCEPT",
                ["director-plan"],
                preferred_provider="provider-a",
                fallback_providers=["provider-b"],
                requirement_keys=["offline"],
            ),
            WorkflowStep("synthesis", "director", "SYNTHESIZE", "CONCEPT_DRAFT", ["product", "technical"]),
            WorkflowStep("review", "reviewer", "REVIEW", "REVIEW_REPORT", ["synthesis"]),
            WorkflowStep("documentation", "documentation-specialist", "DOCUMENT", "FINAL_DOCUMENT", ["review"]),
            WorkflowStep(
                "owner-approval",
                "director",
                "PRESENT_FOR_APPROVAL",
                "APPROVED_RESULT",
                ["documentation"],
                requires_owner_approval=True,
                risk=ActionRisk.PUBLISH,
            ),
        ],
        max_handoffs=10,
        max_retries=6,
        max_review_cycles=2,
        max_agent_calls=16,
    )


def run_v2_benchmark(root: Path) -> tuple[BenchmarkMetrics, dict[str, Any]]:
    providers = {
        "provider-a": ScriptedProviderAdapter("provider-a"),
        "provider-b": ScriptedProviderAdapter("provider-b"),
    }
    traces = LocalTraceService()
    engine = PrototypeWorkflowEngine(JsonCheckpointStore(root), LocalAgentRuntime(providers), traces)
    started = perf_counter()
    state = engine.create_workflow(
        "benchmark-org",
        "Develop a simple household expense application concept, review it and prepare a final document.",
        expense_app_definition(),
        requirements={"offline": False},
    )
    state = engine.run_until_blocked(state.workflow_id)
    if state.status == WorkflowStatus.WAITING_FOR_OWNER:
        state = engine.submit_human_decision(state.workflow_id, "owner-approval", True)
        state = engine.run_until_blocked(state.workflow_id)
    duration_ms = (perf_counter() - started) * 1000
    metrics = BenchmarkMetrics(
        engine="RUNTIME_V2_PROTOTYPE",
        status=state.status,
        agent_calls=state.total_agent_calls,
        handoffs=len(state.handoffs),
        duplicate_work=sum(max(0, step.attempts - 1) for step in state.steps.values()),
        lost_context=0,
        manual_prompt_glue=0,
        recovery_supported=True,
        duration_ms=round(duration_ms, 3),
        artifact_count=len(state.artifacts),
        trace_events=len(traces.list_events(state.workflow_id)),
    )
    return metrics, state.to_dict()


def current_baseline_metrics(duration_ms: float = 0.0, agent_calls: int = 5) -> BenchmarkMetrics:
    """Observed current DirectorService capability baseline.

    The current engine delegates each specialist and an independent reviewer,
    but has no dependency graph, concurrent wave, owner-resume checkpoint or
    typed artifact handoff for the reference workflow.
    """
    return BenchmarkMetrics(
        engine="CURRENT_DIRECTOR_SERVICE",
        status="COMPLETED",
        agent_calls=agent_calls,
        handoffs=0,
        duplicate_work=0,
        lost_context=0,
        manual_prompt_glue=3,
        recovery_supported=False,
        duration_ms=round(duration_ms, 3),
        artifact_count=max(0, agent_calls - 1),
        trace_events=agent_calls * 2,
    )


def metrics_dict(metrics: BenchmarkMetrics) -> dict[str, Any]:
    return asdict(metrics)
