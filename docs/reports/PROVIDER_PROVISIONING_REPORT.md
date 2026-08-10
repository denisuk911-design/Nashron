# Provider Provisioning Report

Status: `IMPLEMENTED_WITH_LIMITATIONS / READY_FOR_USER_TEST`

## Architecture Implemented

- Provider profile model.
- Provider registry.
- Provider health service.
- Provider provisioning service foundation.
- Provider health states for installation/authentication/access/health/capability.
- Employee execution readiness states.
- Provider metadata SQLite tables.
- Agent provider assignments.
- Provisioning session metadata.
- Director Console page `ИИ и CLI`.

## Provider Adapters Implemented

- `CodexProviderAdapter`: uses existing Codex client availability/version/login status.
- `GeminiProviderAdapter`: uses existing Gemini client availability/version/API-key status.
- `MissingProviderAdapter`: used for Claude/future providers without claiming readiness.

## Providers Actually Tested Automatically

Automated tests cover simulated ready/auth-required providers and missing Claude adapter behavior.

Real manual authentication was not performed.

## Installation Flows

No installation commands are executed in Phase 2A.1.

Installation preview, installer adapters and guided install are deferred to Phase 2A.2.

## Authentication Flows

No new authentication flow is launched in Phase 2A.1.

Codex and Gemini reuse existing status checks. Credentials are not stored in SQLite.

## Access Checks

Phase 2A.1 distinguishes `AUTHENTICATED` from `ACCESS_AVAILABLE`, but full bounded access probes are deferred.

## Manual User Actions Still Required

- Open `Команда` -> `ИИ и CLI`.
- Click `Повторить проверку`.
- Confirm provider states.
- Manually verify login flows through official CLIs if needed.

## Provider-Specific Limitations

- Claude is defined but not execution-ready.
- Gemini access is not probed; only API-key presence is checked.
- Codex access is inferred from CLI login status; no model task probe is run automatically.

## Files Created

- `core/provider_models.py`
- `core/provider_service.py`
- `tests/test_provider_provisioning.py`
- `docs/architecture/PROVIDER_PROVISIONING.md`
- `docs/architecture/PROVIDER_ADAPTERS.md`
- `docs/architecture/AUTHENTICATION_AND_SECRETS.md`
- `docs/architecture/EMPLOYEE_EXECUTION_READINESS.md`
- `docs/architecture/FIRST_RUN_SETUP.md`
- `docs/testing/PROVIDER_SETUP_USER_TEST.md`

## Files Modified

- `core/database.py`
- `core/management_models.py`
- `gui/main_window.py`
- `gui/director_console.py`
- architecture migration/data-model/director-console docs.
