# TEAM2050-RUNTIME-V2-BENCHMARK-001

Baseline: `57a4fe7`  
Mode: research -> benchmark -> prototype -> decision  
Production integration: none

## Result

The experiment demonstrates that Team2050 can own a small provider-neutral
runtime contract without immediately adopting a large orchestration framework.
The architecture borrows proven semantics but keeps product entities,
professional development and organizational knowledge under Team2050 control.

## Experiments

| Experiment | Result | Executable evidence |
|---|---|---|
| Provider switch after steps 1-2 | PASS | Provider A calls 1,2,3(unavailable); B calls 3,4,5; step-2 artifact is supplied to step 3; 1-2 have one attempt/effect commit |
| Structured handoff | PASS | Receiver obtains `artifact-source`, expected output, constraints, acceptance and evidence requirements; creates `artifact-review` |
| Better learning promotion | PASS | Current score 0.75, candidate 1.00, no critical regression, version 2 promoted |
| Bad learning rejection | PASS | Candidate introduces a critical regression and remains rejected; current version 1 stays active |
| Employee delete / knowledge retention | PASS | Old identity is absent; validated knowledge remains with deleted-contributor provenance; new hire receives it and the approved skill |
| Provider timeout and tool failure | PASS | Timeout switches A to B; failed tool is checkpointed; restart retries pending work and completes with success/failure evidence |
| Crash after side effect | PASS | Effect is committed before simulated crash; restart reconciles it; provider call count and effect commit count remain exactly one |

Test file: `experiments/runtime_v2/test_runtime_v2_benchmark.py`.

## Decision

Recommend a Team2050-owned thin canonical runtime with optional framework
adapters. Do not add Microsoft Agent Framework, LangGraph, AutoGen, OpenHands,
CrewAI or Langfuse to the production client at this stage.

The next approved step should be a feature-flagged, shadow-state pilot for one
single-agent task with a real CLI provider. It must retain the legacy runtime as
rollback and prove packaged Windows restart, provider switch, artifact evidence
and idempotent tool behavior before any wider migration.

## Unresolved before production

- Choose canonical SQL/event schema and migration ownership.
- Define transaction/outbox behavior for real filesystem and external effects.
- Define secret references that are never embedded in portable state.
- Implement capability negotiation for real CLI/API/MCP adapters.
- Set retention/privacy policies for traces, personal memory and deleted
  contributors.
- Benchmark token/cost/latency with real providers.
- Run packaged GUI acceptance on clean and legacy profiles after integration.
