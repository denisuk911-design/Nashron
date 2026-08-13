# Runtime V2 Research Matrix

Research date: 2026-08-14. Scope: architecture benchmark only. No framework was
added to Team2050 production dependencies.

## Sources and inspected revisions

Only official documentation and official repositories were used.

| Project | Inspected revision | Official sources |
|---|---|---|
| Microsoft Agent Framework | `9645d33cde44603cd3e600c699ec09804212bda3` | [repository](https://github.com/microsoft/agent-framework), [orchestrations](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/), [checkpoints](https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/checkpoints), [HITL](https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/human-in-the-loop) |
| AutoGen | `027ecf0a379bcc1d09956d46d12d44a3ad9cee14` | [repository](https://github.com/microsoft/autogen), [core runtime](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/index.html), [team state](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html), [tools](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/components/tools.html) |
| LangGraph | `644815f9e5bc52ad8f7a5227a456227e9c3e639b` | [repository](https://github.com/langchain-ai/langgraph), [persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts), [functional API](https://docs.langchain.com/oss/python/langgraph/functional-api) |
| OpenHands Software Agent SDK | `ceda00b478a41b64c2f259c096e08977ca7ea4dd` | [repository](https://github.com/OpenHands/software-agent-sdk), [SDK architecture](https://docs.openhands.dev/sdk/arch/sdk), [workspace](https://docs.openhands.dev/sdk/arch/workspace), [persistence](https://docs.openhands.dev/sdk/guides/convo-persistence), [tools and MCP](https://docs.openhands.dev/sdk/arch/tool-system) |
| CrewAI | `4b9b8bcbb9847e5856c3456b38f3bff739b4c4e4` | [repository](https://github.com/crewAIInc/crewAI), [flows](https://docs.crewai.com/en/concepts/flows), [memory](https://docs.crewai.com/en/concepts/memory), [processes](https://docs.crewai.com/en/concepts/processes) |
| Langfuse | `45252d69bff7f0600a014c7b63b703f5a71c5fc3` | [repository](https://github.com/langfuse/langfuse), [trace practices](https://langfuse.com/docs/observability/best-practices), [experiments](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk), [experiment model](https://langfuse.com/docs/evaluation/experiments/data-model) |
| MCP | specification `2025-06-18` | [architecture](https://modelcontextprotocol.io/specification/2025-06-18/architecture) |

Revision hashes are research pins, not vendored dependencies. They identify what
was current when the comparison was made.

## Detailed comparison

Legend: **Strong** means a native, documented mechanism; **Partial** means the
application must provide important semantics; **No** means no suitable native
mechanism was found for this requirement.

| Capability | Current Team2050 | MAF | AutoGen | LangGraph | OpenHands SDK | CrewAI |
|---|---|---|---|---|---|---|
| Execution model | Qt-threaded chat runs plus heuristic autonomy | Typed workflows executed in supersteps | Actor/message runtime plus AgentChat teams | State graph or functional durable tasks | Async agent action/observation loop | Crews plus event-driven Flows |
| Agent state | SQLite profiles/runtime rows, prompt carries too much working state | Executor and shared workflow state | Serializable agent/team state | User-defined graph state | Serializable immutable conversation state | Structured/unstructured Flow state |
| Persistent sessions | Conversation and task rows | Checkpoint manager | `save_state`/`load_state`; running-team snapshot has consistency warning | Thread-keyed checkpointers | Base state plus append-only event files | `@persist`, default SQLite backend |
| Provider abstraction | Codex/Gemini adapters exist, but continuity is not canonical | Model/provider abstraction | Model client abstraction | Framework-neutral nodes; usually LangChain model adapters | LLM/provider-neutral composition | Broad LLM abstraction |
| Tools | Local assistant and provider-specific CLI behavior | Function/tools with approval | Typed tools, workbenches, code executors | Tools are normal nodes/tasks | Typed actions and observations | Rich tool catalogue and custom tools |
| MCP | No neutral runtime boundary | Supported through integrations | MCP workbench/tools | Available through ecosystem adapters | Native discovered MCP tools | Native multiple transports |
| Workspace | Local path services, permissions not an execution contract | Application-owned | Code executors provide isolation choices | Application-owned | Strong local/container/remote workspace abstraction | Tool-specific, less central than OpenHands |
| Handoffs | Mostly prose/peer context; some DB handoff records | Handoff orchestration transfers control | Handoff messages and termination conditions | `Command`/subgraphs/custom state | Conversation/tool oriented, not org handoff-centric | Delegation and Flow transitions |
| Multi-agent coordination | Heuristic routing and bounded peer turns | Sequential, concurrent, handoff, group chat, Magentic | Round-robin, selector, swarm, core actor messaging | Explicit graphs/subgraphs and parallel supersteps | Primarily one software agent; composition possible | Sequential/hierarchical crews and flows |
| Checkpoint/resume | Partial task/run persistence, no canonical side-effect protocol | Strong: executor/shared/pending message/request state | State can persist; custom resume behavior remains agent responsibility | Strong: per-step snapshots and pending-write recovery | Strong conversation restore; workspace effects remain external | Flow state restore/fork; exact effect semantics remain app responsibility |
| Human approval | GUI/permission policy exists, not unified with durable run state | Strong request/response and tool approval | User proxy/handoff patterns | Strong `interrupt`/`Command` | Confirmation/security policies | Human input and Flow feedback |
| Memory | Messages, user memory, skills, knowledge tables, weak separation in prompts | Application-owned | Memory stores and team context | Thread memory plus cross-thread stores | Conversation history, condensers, agent state | Unified memory system and knowledge |
| Skills | Product skill entities, evidence model incomplete | No professional skill lifecycle | No professional skill lifecycle | No professional skill lifecycle | File/repository skills | Agent skills and training concepts |
| Observability | DB runs/events and ad hoc diagnostics | OpenTelemetry integration | Tracing/debug hooks | Callbacks/LangSmith ecosystem | Events and statistics | Built-in tracing and integrations |
| Evaluation | Product metrics and tests; no versioned skill dataset gate | Framework-level eval not the product focus | Benchmarks/evals external | LangSmith/evaluation ecosystem external | Evaluation external to core runtime | Testing/training concepts, not Team2050 qualification semantics |
| Failure recovery | Provider errors handled, but canonical resume/idempotency incomplete | Durable checkpoints and pending requests | Exceptions/cancellation; application owns many recovery rules | Strong checkpoint resume and pending writes | Auto-save state; tool/workspace effects need policy | Persistent Flow state; application owns idempotency |
| Parallel execution | Providers can start together in chat, task graph is not authoritative | Concurrent orchestration | Async runtime/teams/tool calls | Native parallel supersteps | Async loop and remote workspaces | Multiple starts/listeners can run concurrently |
| Cancellation | Qt workers/provider cancellation, not canonical task cancellation | Workflow cancellation facilities | Cancellation token | Stream/task cancellation patterns | Pause/stop execution controls | Async flow/crew controls |
| Context management | ContextSnapshot + PromptBuilder, provenance/token policy incomplete | Agent/application-owned | Model contexts and memory | State selection is application-owned | Condensers, skills, events | Memory/knowledge/planning context |

## What to use, adapt, and reject

### Microsoft Agent Framework

- **USE as reference:** orchestration taxonomy, superstep checkpoints, persisted
  pending HITL requests, typed workflow boundaries.
- **ADAPT:** checkpoint semantics behind Team2050-owned interfaces; management
  policy selects sequential/parallel/handoff/review patterns.
- **DO NOT USE now:** production dependency or framework-owned product state.
  It is broader than the local desktop prototype needs, and current workflow
  APIs must not become Team2050's permanent domain language.

### AutoGen

- **USE as reference:** single-agent-first guidance, typed messages, local to
  distributed runtime continuity, cancellation tokens, explicit termination.
- **ADAPT:** direct/broadcast communication only after Team2050 routing has
  selected participants; save only provider-neutral canonical state.
- **DO NOT USE:** round-robin or selector chat as the primary work engine. It
  encourages conversation as state and can recreate the product's ping-pong
  loops. AutoGen itself warns that team state saved while running may be
  inconsistent.

### LangGraph

- **USE as reference:** durable tasks, per-step checkpoints, pending-write
  recovery, interrupts, idempotency guidance and bounded subgraphs.
- **ADAPT:** deterministic task graph and replay rules behind a small
  `WorkflowEngine` contract.
- **DO NOT USE now:** expose nodes/graphs to users, depend on LangSmith, or put
  business entities in graph-private state. A future adapter remains viable.

### OpenHands

- **USE as reference:** typed action/observation pairs, workspace abstraction,
  path validation, local/container/remote execution, confirmation policy,
  append-only event trail.
- **ADAPT:** workspace and tool boundaries for arbitrary professions, not only
  software development.
- **DO NOT USE:** make Team2050 an OpenHands fork or persist credentials inside
  portable employee state. The SDK's software-agent loop is broader and more
  domain-specific than the universal organization product needs.

### CrewAI

- **USE as reference:** simple user-facing agents/crews/flows, typed Flow state,
  local SQLite persistence and human feedback.
- **ADAPT:** organization templates may select management policies, while the
  runtime remains profession-neutral.
- **DO NOT USE:** role-playing prompts or delegated prose as authoritative
  capability/handoff state; do not accept framework memory as validated
  organizational knowledge.

### Langfuse

- **USE as reference:** trace -> observation -> session hierarchy, stable trace
  naming, datasets, experiment runs, item/run evaluators and regression gates.
- **ADAPT:** local `TraceService` and `EvaluationDataset` schemas first;
  Langfuse/OpenTelemetry can be optional exporters later.
- **DO NOT USE:** cloud service as system of record or LLM-judge score as the
  sole promotion signal.

### MCP

- **USE:** provider-neutral discovery contract for tools, resources and prompts.
- **ADAPT:** Team2050 host enforces organization permissions, approval classes,
  provenance and evidence around every MCP call.
- **DO NOT USE:** treat MCP as an orchestration, memory or authorization system;
  its scope is context/tool exchange and it deliberately does not define those
  application policies.

## Current Team2050 critical gaps

1. Provider adapters exist, but employee task continuity still depends on
   provider prompts and local session behavior. There is no complete canonical
   provider-switch contract.
2. `MainWindow`, prompt construction and chat orchestration still share policy.
   A chat message can indirectly become the work state.
3. Current handoff is not guaranteed to carry concrete artifact IDs,
   acceptance criteria and evidence requirements.
4. Task/run persistence does not define an atomic side-effect/idempotency
   protocol. A crash between a tool effect and state update can duplicate work.
5. Context assembly has useful snapshots but no explicit token budget and
   provenance contract across task/artifact/decision/skill/knowledge sources.
6. Skills, knowledge, standards, experience and source references exist as
   product concepts but their lifecycle and ownership boundaries are not yet
   enforced by one runtime contract.
7. Skill progress is evidence-aware, but there is no versioned evaluation
   dataset comparing current versus candidate behavior before promotion.
8. Employee deletion and organizational knowledge retention are not expressed
   as an executable cross-lifecycle invariant.
9. Traces are fragmented across runs/events/provider logs. They cannot yet show
   one neutral run with context, skills, knowledge, tools, artifacts, handoffs,
   errors and provider changes.
10. Local absolute paths leak into stored settings. Future desktop/server/web
    state needs logical URIs resolved at deployment time.

The prototype in this directory addresses these gaps as executable contracts;
it is not a production implementation.
