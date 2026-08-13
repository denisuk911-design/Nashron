# Team2050 Orchestration Benchmark

Research snapshot: 2026-08-13. Sources are official repositories and official
documentation. The exact inspected commits are listed below.

## Candidates

| Candidate | Version / commit | License | Main architectural value | Main limitation for Team2050 desktop |
|---|---|---|---|---|
| Current Team2050 | repository baseline e14493f | proprietary project | Product entities, UI, provider hub, persistent director plans | Sequential assignments; orchestration coupled to services/database |
| Microsoft Agent Framework | 1.13.0 / `6d25fb1` | MIT | Workflows, concurrent/handoff/group patterns, HITL, checkpointing, telemetry | Meta-package resolved 200 packages and 801.5 MiB in test target; functional workflow API warns experimental |
| LangGraph | 1.2.11 / `644815f` | MIT | Explicit state graph, durable checkpointers, interrupts, resume | Adds graph vocabulary and measured 3.1 s graph API import in isolated Python 3.14 run |
| OpenHands SDK | 1.42.1 / `ceda00b` | MIT | Agent/conversation/tool/workspace execution and security reference | 128-package resolution; software-agent runtime is broader than Team2050 needs |
| AG2 | 1.0.1 / `088f280` | Apache-2.0 | Multi-agent conversation, group chat and handoff patterns | Conversation-first model risks recreating ping-pong; not a durable workforce system |
| Langfuse SDK | 4.14.4 / `e415269` | MIT SDK/core with enterprise directories in server repo | Tracing, evaluation and prompt observability | Optional remote/self-host backend; server stack is inappropriate for local desktop core |
| Temporal Python SDK | 1.31.0 / `73bdb36` | MIT | Strong durable execution and retry semantics | Requires Temporal service; better fit for future cloud control plane |

Official references: [Microsoft Agent Framework](https://github.com/microsoft/agent-framework),
[Agent Framework documentation](https://learn.microsoft.com/en-us/agent-framework/),
[LangGraph](https://github.com/langchain-ai/langgraph),
[LangGraph documentation](https://docs.langchain.com/oss/python/langgraph/overview),
[OpenHands SDK](https://github.com/OpenHands/software-agent-sdk),
[OpenHands architecture](https://docs.openhands.dev/sdk/arch/overview),
[AG2](https://github.com/ag2ai/ag2), [Langfuse](https://github.com/langfuse/langfuse),
and [Temporal Python SDK](https://github.com/temporalio/sdk-python).

## Capability matrix

Legend: Y native/strong, P partial or adapter work, N absent/not suitable.

| Criterion | Current | MAF | LangGraph | OpenHands SDK | AG2 | Chosen V2 abstraction |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| State persistence | Y | Y | Y | Y | P | Y |
| Durable checkpoint/resume | P | Y | Y | P | P | Y |
| Crash recovery policy | P | Y | Y | P | P | Y |
| Multi-agent orchestration | Y | Y | Y | P | Y | Y |
| Typed handoff/artifacts | P | P | P | P | P | Y |
| Parallel dependencies | N | Y | Y | P | P | Y |
| Human approval | P | Y | Y | Y | Y | Y |
| Provider abstraction | Y | Y | Y | Y | Y | Y |
| Tool/workspace isolation | P | P | P | Y | P | Y boundary |
| Skills and employee memory | Y | N | N | P | N | Y |
| Streaming/cancel/timeout | P | Y | Y | Y | P | Contracted |
| Retry by failure reason | P | P | P | P | P | Y |
| Neutral observability | P | OpenTelemetry | callbacks | OpenTelemetry | hooks | TraceService |
| Desktop/local-first | Y | P | Y | P | Y | Y |
| Cloud-ready | P | Y | Y | Y | P | Y boundaries |
| Migration complexity | - | High | Medium | High | Medium | Low now / staged later |

## Dependency and Windows measurements

Measurements used `pip --dry-run --report` and isolated `--target` installs on
Windows, Python 3.14.5. They are environment-specific and intentionally not
generalized as vendor guarantees.

| Package | Resolved distributions | Top-level wheel | Isolated installed size / import observation |
|---|---:|---:|---|
| agent-framework 1.13.0 | 200 | 5.6 KiB meta wheel | 801.5 MiB; base import 233 ms, 6.0 MiB traced peak |
| langgraph 1.2.11 | 35 | 243 KiB | 38.3 MiB; graph API import 3,110 ms, 44.6 MiB traced peak |
| openhands-sdk 1.42.1 | 128 | 778 KiB | Not installed into product environment |
| ag2 1.0.1 | 22 | 853 KiB | Not installed into product environment |
| langfuse 4.14.4 | 26 | 672 KiB | Not installed into product environment |
| temporalio 1.31.0 | 5 | 15.2 MiB Windows wheel | Native core; requires external service for durable execution |

MAF's official checkpoint sample ran successfully and restored completed step
results without another call. A LangGraph StateGraph with `InMemorySaver` also
restored completed state. A minimal LangGraph one-file PyInstaller probe built
to 29.3 MiB and started successfully from a clean Windows temporary directory
in 1.61 seconds. PyInstaller warned only about absent optional `tzdata` in this
probe. Neither dependency was added to production requirements. The
framework-neutral V2 probe packages independently; production packaging remains
unchanged.

## Reference workflow comparison

Fixture: expense application concept with Director, concurrent Product and
Technical work, synthesis, independent review, documentation, owner approval.

| Metric | Current DirectorService | Runtime V2 prototype |
|---|---:|---:|
| Actual agent calls in deterministic fake-provider run | 3 | 7 |
| Explicit stages represented | generic execution + review | all 7 stages |
| Concurrent product/technical wave | no | yes |
| Typed artifact handoffs | no | 7 |
| Owner approval pause/resume | keyword gate before plan | explicit final runtime state |
| Crash recovery | assignment persistence, no running-step recovery contract | completed preserved, running recovered by policy |
| Manual prompt glue needed for exact flow | 3 missing transitions | 0 |
| Prototype runtime duration, fake provider | 369 ms | 36 ms |

Durations measure local orchestration and test doubles, not model latency. More
V2 calls are expected because V2 models the requested stages instead of
collapsing them. The meaningful result is deterministic dependencies, evidence,
resume and control, not the absolute fake-provider timing.

## Conclusion

The benchmark does not justify a big-bang framework migration. Preserve the
Team2050 product layer and adopt its own thin contracts now. LangGraph is the
best first adapter candidate because it supplies durable graph semantics at a
much smaller desktop dependency cost than the current MAF meta-package. MAF
should be reassessed for a cloud runtime or after selecting narrower component
packages. OpenHands should remain an architectural reference for workspace,
tools, confirmation and stuck detection. Langfuse belongs behind TraceService.
