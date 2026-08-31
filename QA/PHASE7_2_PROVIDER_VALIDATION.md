# Phase 7.2 Live Provider Validation

## Verified

- Packaged `dist/Luminifera.exe` provider catalog is read from the real Core API.
- Every provider returned by the catalog completed a real Core health check.
- Active provider/model selection was saved through `/api/settings` and survived
  a packaged restart with an isolated Team2050 profile.
- Isolated packaged save/remove passed with `TEAM2050_TEST_CREDENTIAL_STORE`; no
  real Windows Credential Manager entry was touched.
- Provider states are explicit (`Ready`, `Login required`, `Unavailable`,
  `Busy`, or `Error`); no secret or credential value was read or rendered.
- Packaged result: `scripts/luminifera_phase72_provider_e2e.py` PASS.
- Configured provider count observed without reading secrets: 4.

## Blocker

The runtime metadata path is now wired and unit-tested: selected provider/model
are carried into the external worker and the worker chooses the request model
over its environment default. The final live provider inference gate remains
covered by the separate PHASE 7.4 live-test report; this validation itself uses
an isolated credential store and performs no paid/provider call.

## Evidence

- Packaged provider validation: `scripts/luminifera_phase72_provider_e2e.py`.
- Hub validation: `scripts/luminifera_provider_hub_e2e.py`.
- Provider Hub UI: `?advanced=providers`.
