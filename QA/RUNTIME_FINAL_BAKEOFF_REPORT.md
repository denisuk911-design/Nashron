# Runtime Final Bake-off

Date: 2026-08-31
Status: BLOCKED, no production winner selected

## Raw evidence

`QA/RUNTIME_FINAL_BAKEOFF_MATRIX.json` was produced by `scripts/runtime_bakeoff_matrix.py` with isolated environments and a 45 second subprocess timeout.

| Candidate | Result | Real evidence | Offline import probe |
|---|---|---|---|
| Native | PASS baseline in `experiments/runtime_v2/test_runtime_v2_benchmark.py` | persistent artifacts/evidence/recovery semantics covered by native benchmark | product environment |
| OpenAI Agents SDK | PASS | real model called a tool and wrote `WORK` observation | `openai-agents 0.22.0`, 2655 ms |
| LangGraph | PASS | real model graph called a tool and wrote `WORK` observation | `langgraph 1.2.11`, 971 ms |
| Google ADK | PASS | real model called a tool and wrote `WORK` observation | `google-adk 2.8.0`, 1505 ms |
| AutoGen | PASS | real model called a tool and wrote `WORK` observation | `autogen-agentchat 0.7.5`, 1586 ms |

No 429 or quota diagnostic was returned in this run. No candidate was marked PASS for the complete product Goal matrix because the probes do not cover the required chat/direct-action/multi-agent/long-running/replan/failure/evidence/restart scenarios.

## Blocker

`services/api/app.py` constructs `RuntimeExecutionService` with the Native adapter only. `core/external_runtime_adapters.py` contains normalization classes, but no production executor is registered for any external SDK. The SDK scripts are isolated validation probes, not Core Goal executors: they do not create organization-scoped Team2050 WorkItems, durable artifacts/evidence, review state, or restart checkpoints.

Therefore it is not technically honest to select an external production winner or switch the default runtime. Doing so would make the runtime identifier claim stronger than the actual execution path. Native remains the only validated product runtime until a real external Goal adapter is implemented and benchmarked against the same product scenarios.

## Verification

- `pytest experiments/runtime_v2/test_runtime_v2_benchmark.py tests/test_runtime_selector.py tests/test_runtime_execution_service.py tests/test_external_runtime_adapters.py -q`: `24 passed`
- isolated candidate import probes: all four PASS
- `QA/RUNTIME_FINAL_BAKEOFF_MATRIX.json`: generated with raw candidate evidence
- no UI files changed
