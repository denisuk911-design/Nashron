# Phase 7.2 Live Provider Validation

## Verified

- Packaged `dist/Luminifera.exe` provider catalog is read from the real Core API.
- Every provider returned by the catalog completed a real Core health check.
- Active provider/model selection was saved through `/api/settings` and survived
  a packaged restart with an isolated Team2050 profile.
- Provider states are explicit (`Ready`, `Login required`, `Unavailable`,
  `Busy`, or `Error`); no secret or credential value was read or rendered.
- Packaged result: `scripts/luminifera_phase72_provider_e2e.py` PASS.
- Configured provider count observed without reading secrets: 4.

## Blocker

The full requirement that Iris and the `openai-agents` worker use the selected
provider/model is not yet proven. `/api/chat` currently routes through the
existing Supervisor chat service without a provider/model selection argument,
and the external worker currently reads its model from runtime environment.
The safe smoke therefore does not overwrite or remove any existing protected
credential and does not claim provider execution PASS.

## Evidence

- Packaged provider validation: `scripts/luminifera_phase72_provider_e2e.py`.
- Hub validation: `scripts/luminifera_provider_hub_e2e.py`.
- Provider Hub UI: `?advanced=providers`.
