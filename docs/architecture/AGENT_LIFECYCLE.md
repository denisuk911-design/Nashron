# Agent Lifecycle

Version: 1.0

## States

```text
DRAFT
ACTIVE
SUSPENDED
DISABLED
ARCHIVED
```

## Meaning

- `DRAFT`: profile exists but cannot receive tasks.
- `ACTIVE`: may receive assignments if provider, role and permissions allow it.
- `SUSPENDED`: temporary pause; history is preserved.
- `DISABLED`: no new assignments; retained for audit and history.
- `ARCHIVED`: retired profile; project history remains intact.

## Deactivation Rules

Deactivation must:

- stop new task assignment;
- cancel or reassign active runs safely;
- preserve messages;
- preserve artifacts;
- preserve decisions;
- preserve audit records;
- preserve findings;
- preserve knowledge contributions;
- record owner reason and timestamp.

## Deletion Boundary

Permanent deletion is an advanced destructive configuration action. It must never silently remove project history, authored files, findings or audit records.

## Phase 1 Implementation

`core/management_models.py` defines lifecycle vocabulary.

`core/management_service.py` supports foundation operations:

- seed current Roman/Petr profiles;
- preview profile creation;
- create profile with role and permissions;
- suspend agent;
- reactivate agent.

## Phase 2A Rules

Allowed transitions:

```text
DRAFT -> ACTIVE
DRAFT -> ARCHIVED
DRAFT -> DISABLED
ACTIVE -> SUSPENDED
ACTIVE -> DISABLED
SUSPENDED -> ACTIVE
SUSPENDED -> DISABLED
DISABLED -> ARCHIVED
```

Direct `ACTIVE -> ARCHIVED` is rejected. Disable first, then archive.

Every lifecycle action requires a reason and writes `management_audit_events`.
