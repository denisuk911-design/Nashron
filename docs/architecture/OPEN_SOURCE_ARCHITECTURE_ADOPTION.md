# Open Source Architecture Adoption For Runtime V3

No third-party source code is copied into Team2050. Runtime V3 adopts patterns behind local Team2050 interfaces.

## Microsoft Agent Framework

SOURCE PROJECT: `microsoft/agent-framework`

SOURCE FILE / MODULE:

- `python/README.md`
- `python/samples/getting_started/workflows/orchestration`
- Microsoft Learn Agent Framework handoff orchestration docs

LICENSE: MIT

IDEA ADOPTED:

- Supervisor and orchestration patterns.
- Sequential/concurrent work decomposition.
- Handoff as explicit transfer of responsibility.
- Human-in-the-loop as a workflow state, not casual chat.

HOW TEAM2050 ADAPTS IT:

- `GoalSupervisor` owns planning and assignments.
- `HybridWorkflowEngine` owns WorkItem state transitions.
- Handoffs carry Team2050 artifact IDs and evidence requirements.
- Future `MAFWorkflowEngine` can implement Team2050 `WorkflowEngine` without replacing domain models.

WHAT IS NOT COPIED:

- No Agent Framework API classes.
- No sample code.
- No MAF persistence model.

## LangGraph

SOURCE PROJECT: `langchain-ai/langgraph`

SOURCE FILE / MODULE:

- `libs/langgraph/langgraph/types.py`
- `libs/langgraph/langgraph/pregel/main.py`

LICENSE: MIT

IDEA ADOPTED:

- State graph orientation.
- Durable checkpoint requirement before interrupt/resume.
- Command/resume as explicit continuation.
- Retry/idempotency as state transition behavior.

HOW TEAM2050 ADAPTS IT:

- Runtime V3 checkpoints Team2050 canonical state after meaningful steps.
- `resume()` reloads Team2050 state and does not repeat completed artifacts.
- Review/rework is explicit state, not chat prompt drift.

WHAT IS NOT COPIED:

- No LangGraph persistence implementation.
- No Pregel or StateGraph API dependency.
- No framework-native state model.

## OpenHands Software Agent SDK

SOURCE PROJECT: `OpenHands/software-agent-sdk`

SOURCE FILE / MODULE:

- `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py`
- `openhands-sdk/openhands/sdk/conversation/impl/remote_conversation.py`

LICENSE: MIT

IDEA ADOPTED:

- Agent execution as Action -> Tool -> Observation loop.
- Workspace as execution boundary.
- Tool observations as the evidence source.
- Event correlation between action and observation.

HOW TEAM2050 ADAPTS IT:

- `Action` and `Observation` are Team2050 dataclasses.
- `ToolRuntime` executes bounded filesystem tools inside a workspace.
- Artifact creation requires a successful observation.
- Future OpenHands adapter can sit behind AgentRuntime or ToolRuntime.

WHAT IS NOT COPIED:

- No OpenHands conversation implementation.
- No remote event cache code.
- No SDK dependency.

## AutoGen

SOURCE PROJECT: `microsoft/autogen`

SOURCE FILE / MODULE:

- Official repository and multi-agent conversation patterns.

LICENSE: MIT

IDEA ADOPTED:

- Useful comparison point for agent communication patterns.

HOW TEAM2050 ADAPTS IT:

- Runtime V3 deliberately does not use free-form group chat as goal execution.
- AutoGen remains comparison material only.

WHAT IS NOT COPIED:

- No AutoGen dependency.
- No AutoGen group chat model as foundation.
