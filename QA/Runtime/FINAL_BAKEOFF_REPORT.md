# Runtime Final Bake-off

Status: BLOCKED_PENDING_PROVIDER_CAPACITY

Follow-up: RUNTIME BAKE-OFF PROVIDER NORMALIZATION / UNBLOCK

Goal: Prepare a verified technical specification for a 24 V to 12 V, 5 A converter and select a suitable controller.

Matrix: `QA/Runtime/FINAL_BAKEOFF.json` (3 clean runs per runtime)
Provider route preflight traces: 15 `provider-route-trace.json` files under `QA/Runtime/final_bakeoff/`, one for every runtime/run. The traces use the explicit route supplied to the benchmark; no worker default route is used.

## Results

| Runtime | Result | Evidence |
|---|---|---|
| Native | PASS | 3 clean runs; each produced 3 work items, 2 physical artifacts, 4 evidence refs, review without findings |
| OpenAI Agents SDK | BLOCKED | real subprocess call returned Gemini `429 RESOURCE_EXHAUSTED` |
| LangGraph | BLOCKED | real subprocess call failed inside model node; no valid result |
| Google ADK | BLOCKED | real subprocess call returned `429 RESOURCE_EXHAUSTED` |
| AutoGen | BLOCKED | real subprocess call returned Gemini `429 RESOURCE_EXHAUSTED` |

The external SDKs were invoked from their isolated environments using the same explicit provider route. No fake PASS was generated. The complete matrix is BLOCKED because the shared route is quota-exhausted; no production winner was changed. Native remains the deterministic baseline/fallback. LangGraph was corrected to use `langchain-openai` and the supplied OpenAI-compatible route; its current run now reports provider error rather than a framework/model-node integration error. The existing OpenAI default is intentionally not re-promoted until provider capacity is restored and the same matrix passes.

LangGraph environment package verified: `langchain-openai 1.6.0`.

Checks: Native golden Goal PASS; benchmark script `py_compile` PASS. Full packaged winner E2E and final runtime switch are blocked by external provider capacity, not by a successful external runtime result.
