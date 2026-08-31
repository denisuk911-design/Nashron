# Phase 7.1 Providers and Motion

## Implemented

- Added an opt-in Advanced Provider Hub at `?advanced=providers`; it is not
  exposed in the normal product navigation.
- Provider rows, model labels, readiness, checks, connect, and disconnect use
  the existing provider API and protected credential service.
- Credentials are accepted only through password inputs and are never rendered
  back to the browser.
- Active provider and model selection persist through the existing settings
  service; provider metadata is returned from the real adapter capability
  profile.
- Wheel navigation now ignores touchpad bursts for 650 ms, uses a 28px gesture
  threshold, and keeps one gesture to one screen. Screen transitions are 420ms;
  edge spring remains a single 650ms 16px response.

## Verification

- Packaged build: `dist/Luminifera.exe` rebuilt successfully.
- Provider Hub packaged smoke: PASS (`scripts/luminifera_provider_hub_e2e.py`).
- Provider Hub checks: opens, real provider rows, password-only inputs, no
  rendered secrets, active provider/model controls.
- Packaged visual E2E: PASS at 1920x1080 and 1440x900, all route captures,
  wheel transitions, theme, and edge spring.
- Targeted UI tests: `15 passed`.
- JS syntax: `app.js`, `v37-ui.js`, and `provider-hub.js` PASS.
- `git diff --check`: PASS.
- Full pytest: `565 passed, 2 warnings` in 182.60 seconds.

Final visual and provider approval remains with the owner/reviewer.
