# Runtime Final Bake-off

Status: BLOCKED_PENDING_PROVIDER_CAPACITY

Goal: Prepare a verified technical specification for a 24 V to 12 V, 5 A converter and select a suitable controller.

Matrix: `QA/Runtime/FINAL_BAKEOFF.json`

## Results

| Runtime | Result | Evidence |
|---|---|---|
| Native | PASS | 3 work items, 2 physical artifacts, 4 evidence refs, review without findings |
| OpenAI Agents SDK | BLOCKED | real subprocess call returned Gemini `429 RESOURCE_EXHAUSTED` |
| LangGraph | BLOCKED | real subprocess call failed inside model node; no valid result |
| Google ADK | BLOCKED | real subprocess call returned `429 RESOURCE_EXHAUSTED` |
| AutoGen | BLOCKED | real subprocess call returned Gemini `429 RESOURCE_EXHAUSTED` |

The external SDKs were invoked from their isolated environments; no fake PASS was generated. A production winner was not changed because no external candidate produced a current real PASS. Native remains the deterministic baseline/fallback. The existing OpenAI default is intentionally not re-promoted from this run until provider capacity is restored and the same matrix passes.

Checks: Native golden Goal PASS; benchmark script `py_compile` PASS. Full packaged winner E2E and final runtime switch are blocked by external provider capacity, not by a successful external runtime result.
