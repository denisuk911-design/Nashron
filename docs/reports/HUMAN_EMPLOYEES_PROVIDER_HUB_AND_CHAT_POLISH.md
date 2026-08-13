# Team2050: human employees, provider hub and chat polish

Date: 2026-08-13  
Release: 2.6.0

## Result

This stage separates four concerns that previously leaked into one another: chat rendering, provider capacity, employee identity and connection provisioning. The UI now renders the owner's message before persistence and routing, provider runs are capacity-limited, generated employees receive editable human communication profiles, and the application ships its own verified background collections.

## Chat send pipeline

`MainWindow.send_message()` now performs only the latency-sensitive UI work synchronously:

1. record `send_clicked`;
2. add the owner's bubble and record `bubble_created`;
3. clear and refocus the composer;
4. return to the Qt event loop;
5. persist, route and start providers from a zero-delay continuation.

Every send records a JSON trace in `app_events` with timestamps for event-loop return, persistence, routing, queued runs, typing, provider start, response readiness and rendering. The Director Console exposes recent traces and the bubble latency budget. A regression test proves that persistence and routing do not happen before the continuation and that the bubble exists first.

Team calls use `ProviderScheduler`. It limits total active processes according to machine load and applies per-provider concurrency limits instead of starting every employee process at once. Queued employees show a real queue state; rejected or completed launches clear it.

## Human employee identity

Employee profiles now persist these independent fields:

- full, preferred and informal names;
- gender and editable biography;
- avatar;
- communication profile: directness, warmth, formality, humour, assertiveness, verbosity, initiative and disagreement style;
- profession, roles and provider remain separate operational data.

The generator uses a 50/50 Ukrainian/international origin decision and a much larger combinatorial pool. The profession no longer becomes the employee's name or dominates every social reply. The prompt uses the communication profile to shape tone while retaining role discipline during real work.

Generation validation covers 500 identities. The golden test requires at least 300 distinct names and a Ukrainian share between 40% and 60%. The packaged catalog contains 96 valid selectable avatars; source sheets are excluded and every valid catalog entry is eligible for generation.

## Theme backgrounds

The release includes 12 original generated bitmap backgrounds, two in each collection:

- city;
- forest;
- ocean;
- mountains;
- night city;
- space.

The manifest records generator, date, license and per-collection provenance. Themes select their matching collection. Rotation supports a new image per launch, a deterministic daily image and a remembered image. The remembered selection is persisted across restarts. “Другой фон” changes the built-in image immediately without restarting.

Custom wallpaper has priority over the built-in collection. Independent controls cover opacity, darkening, blur and placement (`cover`, `fit`, `center`, `stretch`, `tile`).

## AI and connections

The Director Console section is named “ИИ и подключения” / “ШІ та підключення” / “AI and connections”. It lists connection type, honest support state, installation, authentication, health, capability matrix and assigned employees.

The catalog contains 24 provider profiles:

- fully supported adapters: Codex CLI and Gemini CLI;
- experimental definitions without a production execution adapter: Claude Code and GitHub Copilot CLI;
- catalog-only API, gateway and local runtimes: OpenAI, Anthropic, Gemini API, DeepSeek, Azure OpenAI, Mistral, Groq, OpenRouter, Bedrock, Vertex AI, GitHub Models, Cerebras, Cohere, Together, Ollama, LM Studio, llama.cpp, vLLM, LocalAI and NVIDIA NIM.

DeepSeek is represented as API-only and has no invented CLI installer. Lifecycle buttons are enabled only when the catalog has a structured official command for that action. The program never constructs shell commands from user text.

API secrets are written to Windows Credential Manager through `WindowsCredentialStore`; SQLite stores only a non-secret credential reference in the audit event. Secrets are not written to logs or employee profiles.

Primary implementation references:

- Codex: <https://developers.openai.com/codex>
- Gemini CLI: <https://github.com/google-gemini/gemini-cli>
- Claude Code: <https://docs.anthropic.com/en/docs/claude-code/getting-started>
- GitHub Copilot CLI: <https://docs.github.com/en/copilot/how-tos/copilot-cli/cli-getting-started>
- OpenAI API: <https://platform.openai.com/docs/quickstart>
- DeepSeek API: <https://api-docs.deepseek.com/>

## Package validation

`validate_product_assets()` checks the theme manifest and files, the avatar catalog, WAV headers when bundled audio exists, localization coverage and PyInstaller data declarations. The current result is ready with one explicit warning: notification sounds use the existing runtime-generated fallback rather than bundled WAV files.

`Team2050.spec` now packages both avatars and theme backgrounds.

## Verification

- Python compile check: passed.
- Focused scheduler, provider, theme, identity, asset and GUI tests: 29 passed.
- Full automated suite: 292 passed in 87.56 seconds.
- Asset validator: passed, 0 errors and 1 documented audio fallback warning.
- Packaged EXE smoke: recorded after the final build below.

## Honest limitations

Only Codex CLI and Gemini CLI currently have complete production execution paths. Catalog entries do not become working agents until an adapter implements invocation, cancellation, streaming, capability checks and error normalization. Claude Code and GitHub Copilot CLI remain experimental for this reason. API and local-runtime profiles are discovery/provisioning records, not pretend implementations.

The identity system gives agents persistent editable style data; it does not claim that a language model has a human biography or independently acquires knowledge without verified artifacts. Skill progress remains evidence-based elsewhere in Team2050.
