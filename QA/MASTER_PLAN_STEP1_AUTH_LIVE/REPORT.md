# MASTER PLAN STEP 1

- Status: local and packaged auth PASS; live Render gate PASS.
- Product commit: `e127798e18c5741bd685b9219ce371fb4fc09aeb`.
- Evidence commit: `1f01f33`.
- Live URL: `https://nashron.onrender.com/app`.
- Live build: `e127798e18c5741bd685b9219ce371fb4fc09aeb`.
- Root cause: first-run detection used protected admin security, and auth bootstrap sent a JavaScript object instead of JSON, producing `422 json_invalid`.
- Fix: public secret-free `/api/auth/bootstrap-status`, correct JSON serialization, Iris auth presence, complete RU/UK/EN auth copy and concrete validation errors.
- Verification: `578 passed`, 2 warnings; packaged fresh profile `bootstrap-status 200 -> bootstrap 201 -> login 200`; live `bootstrap-status 200`, Iris media loaded, no console errors.
- Captures: `auth-1920x1080.png`, `auth-1440x900.png` in this directory locally; `manifest.json` contains live response evidence.
- MCP delivery: pending because Playwright Extension is currently unresponsive even to `browser_tabs`.
