# Runtime Recommendation

Status: `CANDIDATE RECOMMENDATION - promotion pending parity gate`

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
