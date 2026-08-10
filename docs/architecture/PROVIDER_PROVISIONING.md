# Provider Provisioning

Phase: 2A.1 foundation.

AI employees are not execution-ready merely because an `AgentProfile` exists. ROMAN2025 now separates:

- provider definition;
- local installation;
- authentication state;
- access state;
- capability status;
- employee provider assignment;
- employee execution readiness.

## Implemented In Phase 2A.1

- `ProviderProfile` model.
- Provider lifecycle states.
- Provider registry with built-in definitions for:
  - `CODEX_CLI`;
  - `GEMINI_CLI`;
  - `CLAUDE_CLI`.
- Lightweight health checks for existing Codex/Gemini integrations.
- Non-ready Claude placeholder definition; no fake Claude readiness.
- Provider health metadata tables.
- Agent provider assignment table.
- Provisioning session metadata table.
- Director Console page `ИИ и CLI`.
- Employee readiness calculation.

## Not Implemented Yet

- automatic CLI installation;
- installation command execution;
- browser/device authentication UI;
- real bounded model capability probes;
- setup wizard on first launch;
- Claude execution adapter.

## Provider Health Dimensions

Installation:

```text
NOT_INSTALLED
DETECTED
INSTALLATION_REQUIRED
INSTALLING
INSTALLED
UPDATE_REQUIRED
INSTALLATION_FAILED
UNSUPPORTED
```

Authentication:

```text
NOT_AUTHENTICATED
AUTHENTICATION_REQUIRED
AUTHENTICATION_IN_PROGRESS
AUTHENTICATED
AUTHENTICATION_EXPIRED
AUTHENTICATION_FAILED
USER_ACTION_REQUIRED
```

Access:

```text
NOT_CHECKED
ACCESS_AVAILABLE
ACCESS_LIMITED
PLAN_INCOMPATIBLE
QUOTA_EXCEEDED
BILLING_REQUIRED
PROVIDER_REJECTED
UNKNOWN
```

Health:

```text
READY
DEGRADED
NOT_READY
BLOCKED
UNKNOWN
```

## Safety

Phase 2A.1 never downloads or installs provider software. Future installation flows must require explicit owner confirmation and command preview.
