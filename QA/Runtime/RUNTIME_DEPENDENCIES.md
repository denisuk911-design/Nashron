# Runtime Candidate Dependencies

Date: 2026-08-30  
Python used for isolated environments: `3.14.5`

The application `.venv` was not modified. Candidate dependencies are isolated
under `.runtime_envs` and ignored by Git.

| Candidate | Environment | Installed version | Import/object smoke | Model-backed smoke |
| --- | --- | ---: | --- | --- |
| OpenAI Agents SDK | `.runtime_envs/openai-agents` | `openai-agents 0.22.0` | PASS | pending credentials |
| LangGraph | `.runtime_envs/langgraph` | `langgraph 1.2.11` | PASS | pending model adapter |
| Google ADK | `.runtime_envs/google-adk` | `google-adk 2.8.0` | PASS | PASS: bounded `gemini-3.6-flash` classification |
| AutoGen | `.runtime_envs/autogen` | `autogen-agentchat 0.7.5`, `autogen-ext 0.7.5` | PASS | pending provider credentials |

## Installation policy

- OpenAI: `pip install openai-agents`
- LangGraph: `pip install langgraph`
- Google: `pip install google-adk`
- AutoGen: `pip install autogen-agentchat "autogen-ext[openai]"`

Each command was run in its own virtual environment. No framework is imported
by the core application at startup. The exact resolved dependency graph is
available from each environment's `pip freeze` and can be regenerated from the
commands above.

## Current smoke boundary

`scripts/runtime_candidate_smoke.py` proves real package import and minimal
object/graph construction without network access or credentials. It does not
claim a model-backed PASS. Phase 6 must add bounded model-backed runs, record
provider/auth results and reject candidates that only import successfully.
