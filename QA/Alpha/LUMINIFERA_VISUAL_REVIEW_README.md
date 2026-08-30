# Luminifera Visual Review Package

This package contains the current Web Alpha evidence captured from the packaged launcher and the latest validated Web screens.

## Captures

- `packaged-landing.png` - product landing
- `packaged-home-real.png` - populated Home workspace
- `packaged-iris-real.png` - Iris workspace
- `packaged-team-real.png` - Team workspace
- `packaged-work-real.png` - Work workspace
- `packaged-files-real.png` - Files workspace
- `phase15_connections_actual.png` - live provider connections view
- `phase16_profile_actual.png` - live owner profile view

## Evidence

- `luminifera_web_packaged_e2e.json` - packaged E2E result
- `EXECUTION_LOG.md` - implementation and verification log
- `LUMINIFERA_ALPHA_REVIEW.zip` - previous Alpha evidence package
- `apps/web/static/app.html`, `apps/web/static/app.css`, `apps/web/static/alpha.js` - current UI source snapshot
- `dist/Luminifera.exe` - locally built executable; binary is intentionally not committed to Git

## Known limitations

- Live BYOK credentials were not included in the test environment.
- Provider connections, Feedback and Diagnostics are implemented and API-tested; a separate full-page screenshot of the Settings subviews needs a stable browser capture session because the extension switched tabs during capture.
- This package is evidence for human visual review, not a claim of final visual acceptance.
