# Luminifera Security Review Package

Status: internal security gate evidence, external production review required.
Baseline commit: `caa8f0f`

## Scope and trust boundaries

- Browser/Product UI is untrusted and calls FastAPI only; it does not write the database.
- FastAPI is the application boundary and delegates mutations to Core/Application Services.
- SQLite is local durable storage; foreign keys are enabled and checked by the health endpoint.
- Provider credentials are accepted only by the provider service and are never returned by read models, logs, or audit payloads.
- A bearer token is an opaque client secret; only its SHA-256 digest is persisted.

## Auth and account flows

`bootstrap (fresh profile only) -> owner login -> Admin enables registration -> member registration -> login/me -> logout or password rotation`.

Bootstrap is closed when any privileged account exists. Registration is disabled by default. Passwords use PBKDF2-HMAC-SHA256 with a per-account 128-bit random salt and 210,000 iterations. Sessions expire after 24 hours, are revocable, and are invalidated on password change or Admin revoke-all.

## Controls reviewed

| Area | Control | Evidence |
| --- | --- | --- |
| Enumeration | Login uses one generic invalid/blocked response; registration is policy-gated | `tests/test_admin_center.py` |
| Brute force | Persistent failed-attempt window and configurable threshold | Phase 5/6 tests and packaged smoke |
| Session fixation | New random token and session id per login; token digest only | `core/auth_service.py` |
| Privilege escalation | Role resolved from durable account/session; member Admin access denied | targeted and packaged tests |
| Last owner | Final active owner cannot be downgraded | Phase 6 test |
| Org isolation | Account session carries organization context; Admin member boundary denied | existing full regression |
| Headers | `nosniff`, frame deny, same-origin referrer, auth no-store | Phase 5 test |
| Secrets | No plaintext credentials in response/read models/audit | provider/admin tests |
| Persistence | Bootstrap closure, credentials, status and session revocation survive restart | packaged smoke |

## Known limitations / external review

- OAuth is a future adapter; public registration is OFF by default.
- External deployment must provide TLS, a production session transport policy, centralized rate limiting and operational secret rotation.
- CSRF is not applicable to bearer-only auth endpoints; if cookie auth is introduced, add CSRF protection before enabling it.
- First-owner bootstrap is intentionally local/fresh-install only and must be reviewed before multi-tenant public deployment.

## Reproduction matrix

1. Fresh profile: bootstrap owner; repeat bootstrap must return `409 owner_bootstrap_closed`.
2. Owner: enable registration; register member; member Admin access must return `403`.
3. Owner: block member; member login must return `401`.
4. Owner: rotate password; old bearer session must return `401`; new login must work.
5. Restart packaged app; bootstrap remains closed and account state persists.
6. Run `pytest -q`, targeted admin tests, `node --check`, `py_compile`, and `git diff --check`.
