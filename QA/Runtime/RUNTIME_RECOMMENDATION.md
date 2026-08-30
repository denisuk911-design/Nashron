# Runtime Recommendation

Status: `BLOCKED_BY_EXTERNAL_QUOTA - Native baseline retained`

Native Runtime remains the production baseline and fallback. External runtime
selection must wait for the model-backed bake-off in
`QA/Runtime/BAKEOFF_RESULTS.md`. Current package/object evidence is not enough
to recommend OpenAI Agents, LangGraph, Google ADK or AutoGen for production.

Evidence currently suggests a split by policy rather than one universal
winner: OpenAI Agents is a candidate for short managed/direct runs, LangGraph
for durable graph-oriented work, Google ADK for its verified Gemini path, and
AutoGen for team-style conversation. This is not a production promotion.

The selector is intentionally conservative: deterministic workflows stay on
Native, and an external adapter failure falls back to Native while recording
the reason. Promotion requires real bounded execution, normalized tool and
observation events, product-owned artifact/evidence references, and
restart/failure evidence for each selected path.

## Required recommendation fields

```text
BEST_CONVERSATIONAL_RUNTIME: OpenAI Agents SDK candidate; promotion pending
  normalized artifact/restart parity.
BEST_MANAGER_RUNTIME: OpenAI Agents SDK candidate; real bounded model/tool
  evidence exists, but no production promotion yet.
BEST_DYNAMIC_MULTI_AGENT_RUNTIME: LangGraph candidate for graph-native
  branching; full multi-agent/tool/recovery bake-off pending.
BEST_LONG_RUNNING_RUNTIME: LangGraph candidate; persistence/recovery fit is
  strongest, but end-to-end parity is not yet proven.
BEST_DETERMINISTIC_RUNTIME: Native Runtime baseline.
BEST_LOCAL_PRIVATE_PATH: Native Runtime; no external candidate has passed a
  local/private inference gate in this migration.
NATIVE_RUNTIME_FUTURE: Protected baseline and deterministic fallback while
  external candidates mature.
OPENAI_AGENTS_FUTURE: Keep as the first external adapter candidate.
LANGGRAPH_FUTURE: Keep for durable and branching execution after parity gate.
GOOGLE_ADK_FUTURE: Keep for evaluation; tool smoke remains quota-blocked.
AUTOGEN_FUTURE: Keep for team-style collaboration after normalized parity.
RECOMMENDED_DEFAULT: Native Runtime until candidate gate passes.
RECOMMENDED_ROUTING_POLICY: deterministic_workflow -> Native; other policies
  may use an explicitly registered, health-checked promoted adapter, with
  safe fallback only before an external side effect is committed.
MIGRATION_RISKS: provider quota, SDK drift, incomplete external artifact/
  recovery parity, and accidental organization/permission bypass.
NEXT_ACTION: rerun blocked provider-backed tool/recovery smokes with valid
  quota, then benchmark all candidates using the same Product fixtures.
```

This is an evidence-based candidate recommendation, not a claim that the
external adapters have already passed the production gate. The next permitted
step is to rerun the blocked provider-backed probes with a valid alternative
credential, then repeat the same normalized parity scenarios before any
promotion.
