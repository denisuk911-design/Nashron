# Luminifera Visual Review Package

This package contains the current Web Alpha evidence captured from the packaged launcher with the isolated `scripts/capture_visual_gate.py` runner.

## Captures

- `standalone/landing.png` - product landing
- `standalone/home.png` - populated Home workspace
- `standalone/iris.png` - Iris workspace
- `standalone/team.png` - Team workspace
- `standalone/work.png` - Work workspace
- `standalone/files.png` - Files workspace
- `standalone/settings.png` - Settings with provider connections, Feedback and Diagnostics
- `standalone/feedback.png` - same real Settings screen captured from the Feedback section

## Evidence

- `luminifera_web_packaged_e2e.json` - packaged E2E result
- `standalone/manifest.json` - capture status, URL and screen list
- `standalone/capture_visual_gate.py` - isolated local Chromium capture helper
- `EXECUTION_LOG.md` - implementation and verification log
- `LUMINIFERA_ALPHA_REVIEW.zip` - previous Alpha evidence package
- `apps/web/static/app.html`, `apps/web/static/app.css`, `apps/web/static/alpha.js` - current UI source snapshot
- `dist/Luminifera.exe` - locally built executable; binary is intentionally not committed to Git

## Known limitations

- Live BYOK credentials were not included in the test environment.
- Provider connections, Feedback and Diagnostics are implemented and API-tested. The current product exposes them as sections of one Settings screen, so `byok`/`feedback` evidence is intentionally not presented as a separate route.
- This package is evidence for human visual review, not a claim of final visual acceptance.
