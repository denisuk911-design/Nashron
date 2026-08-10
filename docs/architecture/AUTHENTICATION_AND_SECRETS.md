# Authentication And Secrets

Provider authentication must be provider-controlled. The application must not ask users to paste passwords into ROMAN2025.

## Rules

- Do not store provider tokens in SQLite.
- Do not store API keys in ordinary JSON configuration files.
- Do not export secrets.
- Prefer official CLI credential storage, OS credential storage or explicit environment variables.
- Store only safe metadata: provider ID, account label, credential reference ID, authentication status and last verification time.

## Phase 2A.1 Behavior

- Codex auth status is checked through existing Codex CLI status support.
- Gemini auth status is inferred from configured API-key availability only.
- No passwords or tokens are captured.
- Provider diagnostics are redacted before persistence.

## Future Authentication UI

Future UI may show:

- provider;
- account label where safe;
- required user action;
- current state;
- retry;
- cancel;
- open terminal/browser;
- verify again.

It must not intercept browser credentials.
