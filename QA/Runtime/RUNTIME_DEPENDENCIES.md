# Runtime Candidate Dependencies

Date: 2026-08-30  
Python used for isolated environments: `3.14.5`

The application `.venv` was not modified. Candidate dependencies are isolated
under `.runtime_envs` and ignored by Git.

| Candidate | Environment | Installed version | Import/object smoke | Model-backed smoke |
| --- | --- | ---: | --- | --- |
| OpenAI Agents SDK | `.runtime_envs/openai-agents` | `openai-agents 0.22.0` | PASS | PASS: bounded `Runner.run` classification |
| LangGraph | `.runtime_envs/langgraph` | `langgraph 1.2.11`, `langchain-google-genai 4.3.7` | PASS | PASS: bounded graph model classification |
| Google ADK | `.runtime_envs/google-adk` | `google-adk 2.8.0` | PASS | PASS: bounded `gemini-3.6-flash` classification |
| AutoGen | `.runtime_envs/autogen` | `autogen-agentchat 0.7.5`, `autogen-ext 0.7.5` | PASS | PASS: bounded client classification |

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
object/graph construction without network access or credentials. The three
model probes use bounded real calls; OpenAI Agents and AutoGen tool probes also
write physical temporary artifacts. Google ADK's tool retry currently receives
provider quota `429`, so it is recorded as `PARTIAL`, not PASS.
