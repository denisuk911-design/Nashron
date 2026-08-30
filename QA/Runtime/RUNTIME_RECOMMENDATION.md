# Runtime Recommendation

Status: `NOT YET DECIDED`

Native Runtime remains the production baseline and fallback. External runtime
selection must wait for the model-backed bake-off in
`QA/Runtime/BAKEOFF_RESULTS.md`. Current package/object evidence is not enough
to recommend OpenAI Agents, LangGraph, Google ADK or AutoGen for production.

The selector is intentionally conservative: deterministic workflows stay on
Native, and an external adapter failure falls back to Native while recording
the reason. Promotion requires real bounded execution, normalized events,
product-owned artifact/evidence references and restart/failure evidence.
