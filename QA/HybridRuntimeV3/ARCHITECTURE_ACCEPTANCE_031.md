# TEAM2050-V3 Architecture Acceptance 031

Status: `COMPLETE` for the Runtime V3 migration milestone.

This is an implementation acceptance audit, not an adoption decision for third-party
frameworks. Team2050 remains the owner of organization, employee, goal, work item,
artifact, evidence, finding and provider-binding data.

## Pattern Check

| Reference pattern | Team2050 implementation | Result |
| --- | --- | --- |
| Supervisor-owned orchestration and explicit handoff | `GoalSupervisor`, dependency graph and typed `Handoff` records | PASS |
| Durable checkpoint and restart | `JsonCheckpointRepository`, persisted `RuntimeState`, resume and HITL tests | PASS |
| Action -> Tool -> Observation | `ProviderAgentRuntime` proposes `Action`; `ToolRuntime` creates typed `Observation`; artifacts require success | PASS |
| Review/rework before completion | independent review creates a finding; owner creates a higher artifact revision | PASS |
| Human interruption/resume | `HitlInterrupt` is persisted and resumed through the packaged GUI smoke | PASS |
| Concurrent independent work | bounded provider executor with deterministic effect commit | PASS |
| Provider capability and contract safety | capability negotiation, contract handshake, circuit health and credential-isolated process environment | PASS |
| MCP-style tool safety | explicit registry, permissions and typed tool observations; no arbitrary provider tool call is trusted | PASS |

## External References

- Microsoft Agent Framework: [handoff orchestration](https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/handoff) and [checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints).
- LangGraph: [interrupt and durable resume](https://docs.langchain.com/oss/python/langgraph/interrupts).
- Model Context Protocol: [tool safety and authorization](https://modelcontextprotocol.io/specification/2025-03-26/index).

The audit intentionally maps concepts instead of importing those frameworks into the
desktop client. This keeps Team2050 state portable and avoids a framework-owned
organization model.

## Acceptance Evidence

- `tests/runtime_v3/test_hybrid_runtime.py` and `tests/test_runtime_v3_service.py` cover planning, evidence, review/rework, resume, concurrent execution, provider contracts and failure boundaries.
- `scripts/runtime_v3_autonomous_org_e2e.py` drives the packaged `Team2050.exe` through the Golden Goal and HITL restart path.
- Packaged evidence is written to `QA/HybridRuntimeV3/runtime_v3_packaged_gui_smoke.json` and its screenshot.
- `PRAGMA foreign_key_check = []` is required for both packaged smoke profiles.

## Non-Blocking Follow-Up

- JSON checkpoints remain the current single-process durable store. A SQLite V3 repository is a future migration, not an acceptance blocker.
- External framework adapters and remote MCP transports remain optional integrations behind the current Team2050 contracts.
