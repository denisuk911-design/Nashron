# Runtime Bake-off Results

Status: `PARTIAL - candidate gate not passed`  
Date: 2026-08-30

## Evidence collected

| Candidate | Package evidence | Local execution evidence | Model-backed result | Gate |
| --- | --- | --- | --- | --- |
| Native | Existing `RuntimeV3GoalService` and 63 targeted runtime tests | Existing Native goal/tool/artifact/review tests | PASS for baseline | BASELINE |
| OpenAI Agents | `openai-agents 0.22.0`, object construction PASS | Agent object only | Not run; no OpenAI API credential | PENDING |
| LangGraph | `langgraph 1.2.11`, graph construction PASS | Real compiled graph invoke: `1 -> 2` | No model configured | PENDING |
| Google ADK | `google-adk 2.8.0`, object construction PASS | Real `InMemoryRunner` execution | PASS: real model classification `WORK` with bounded run | CANDIDATE |
| AutoGen | `autogen-agentchat/autogen-ext 0.7.5`, object construction PASS | Agent/client objects only | Not run; no provider run configured | PENDING |

## Interpretation

The four external packages are real installed candidates in isolated
environments. LangGraph has a local graph execution proof, and Google ADK has
one bounded real model-backed execution. This is candidate evidence, not a
production promotion: OpenAI Agents and AutoGen still require their own
bounded model-backed runs, and all candidates still need normalized tool/
artifact/restart evidence. The migration must not route production Product
work to an external candidate solely because its import succeeds.

## Next evidence required

- bounded model-backed execution for each candidate where credentials and
  provider access are available;
- normalized tool/observation events and artifact references;
- failure/restart and duplicate-side-effect checks;
- actual adapter execution through `RuntimeSelector`.
