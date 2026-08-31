# Packaged V3 diagnostic mode

Commit under test: `d88d34a` plus diagnostic-mode changes.

Launch the packaged client with:

`Luminifera.exe` then open `/app?diagnostics=1` in the local browser.

Verified packaged result:

- Application API: reachable, HTTP 200.
- Current organization: shown by name only.
- Iris, Team, Work, Files and Feedback: each reachable, HTTP 200.
- Background and Iris sources: shown from `config.js`.
- No secrets, tokens, raw IDs or runtime/provider internals rendered.
- Normal `/app`: diagnostic panel hidden and existing Product UI unchanged.
- Global vertical scroll remains absent.

The diagnostic panel is fixed and query-gated; it is not part of the normal Product UI composition and does not create fake records or mutate data.
