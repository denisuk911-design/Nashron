# Runtime Bake-off Results

Status: `PARTIAL - candidate gate not passed`  
Date: 2026-08-30

## Evidence collected

| Candidate | Package evidence | Local execution evidence | Model-backed result | Gate |
| --- | --- | --- | --- | --- |
| Native | Existing `RuntimeV3GoalService` and 63 targeted runtime tests | Existing Native goal/tool/artifact/review tests | PASS for baseline | BASELINE |
| OpenAI Agents | `openai-agents 0.22.0` | Real `Runner.run` through SDK | PASS: real model classification `WORK` | CANDIDATE |
| LangGraph | `langgraph 1.2.11` + `langchain-google-genai 4.3.7` | Real compiled graph node with model | PASS: real model classification `WORK` | CANDIDATE |
| Google ADK | `google-adk 2.8.0`, object construction PASS | Real `InMemoryRunner` execution | PASS: real model classification `WORK` with bounded run | CANDIDATE |
| AutoGen | `autogen-agentchat/autogen-ext 0.7.5` | Real `OpenAIChatCompletionClient.create` | PASS: real model classification `WORK` | CANDIDATE |

## Interpretation

The four external packages are real installed candidates in isolated
environments. LangGraph, Google ADK, OpenAI Agents and AutoGen each have one
bounded real model-backed execution.
This is candidate evidence, not a production promotion: all candidates still
need normalized tool/artifact/restart evidence. The migration must not route
production Product work to an external candidate solely because its import
succeeds.

## Next evidence required

- normalized tool/observation events and artifact references;
- failure/restart and duplicate-side-effect checks;
- actual adapter execution through `RuntimeSelector`.

The real SDK probe scripts are `runtime_google_adk_real_smoke.py`,
`runtime_openai_agents_real_smoke.py`, and `runtime_autogen_real_smoke.py`.
