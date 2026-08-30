# Runtime Bake-off Results

Status: `PARTIAL - blocked candidates explicitly excluded from promotion`  
Date: 2026-08-30

## Evidence collected

| Candidate | Package evidence | Local execution evidence | Model-backed result | Gate |
| --- | --- | --- | --- | --- |
| Native | Existing `RuntimeV3GoalService` and 63 targeted runtime tests | Existing Native goal/tool/artifact/review tests | PASS for baseline | BASELINE |
| OpenAI Agents | `openai-agents 0.22.0` | Real `Runner.run` through SDK | PASS: real model classification `WORK`; tool/artifact PASS recorded | KEEP_FOR_FUTURE |
| LangGraph | `langgraph 1.2.11` + `langchain-google-genai 4.3.7` | Real compiled graph node with model | PASS: real model classification `WORK` | CANDIDATE |
| Google ADK | `google-adk 2.8.0` | Real `InMemoryRunner` model run; tool retry hit provider quota | Model PASS; tool/artifact smoke BLOCKED by `429 RESOURCE_EXHAUSTED` | PARTIAL |
| AutoGen | `autogen-agentchat/autogen-ext 0.7.5` | Real `OpenAIChatCompletionClient.create` | PASS: real model classification `WORK`; tool/artifact PASS recorded | KEEP_FOR_FUTURE |

## Interpretation

The four external packages are real installed candidates in isolated
environments. LangGraph, Google ADK, OpenAI Agents and AutoGen each have one
bounded real model-backed execution.
This is candidate evidence, not a production promotion: Google ADK tool
evidence is blocked by the provider free-tier quota, and all candidates still
need normalized tool/artifact/restart evidence. The migration must not route
production Product work to an external candidate solely because its import
succeeds.

Per the owner instruction to skip the quota-blocked live stage, LangGraph and
Google ADK are explicitly excluded from promotion. OpenAI Agents and AutoGen
remain installed, evidenced candidates, but are also kept for future promotion
until the real SDK subprocess bridge is exercised in the same environment as
the normalized adapter.

## Next evidence required

- normalized tool/observation events and artifact references;
- failure/restart and duplicate-side-effect checks;
- actual adapter execution through `RuntimeSelector`.

The real SDK probe scripts are `runtime_google_adk_real_smoke.py`,
`runtime_openai_agents_real_smoke.py`, and `runtime_autogen_real_smoke.py`.

The reproducible latest matrix is `QA/Runtime/BAKEOFF_MATRIX.json`. Its
bounded rerun recorded OpenAI Agents tool/artifact PASS and quota failures for
the other three provider-backed probes; earlier successful model smokes are
preserved above and are not overwritten by transient availability.

## Normalized execution checkpoint - 2026-08-30

- `ExternalExecutionPayload` now carries explicit `tool_calls`; adapters emit
  `tool.called` before observations and artifact events.
- An external LangGraph result is persisted through `RuntimeExecutionJournal`
  and recovered after constructing a fresh journal instance. Cross-organization
  recovery remains denied.
- The LangGraph real smoke now executes a graph-native observation/artifact
  node after the model node. The current rerun reached the real model path but
  was rejected by the documented Gemini `429 RESOURCE_EXHAUSTED` quota; no
  artifact was counted as a live provider PASS for that run.
