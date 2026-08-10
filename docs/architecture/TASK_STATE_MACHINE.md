# Task State Machine

Version: 1.0

## States

- `NEW`
- `REQUIREMENTS_DRAFT`
- `READY_FOR_DESIGN`
- `IN_DESIGN`
- `READY_FOR_REVIEW`
- `IN_REVIEW`
- `REWORK_REQUIRED`
- `READY_FOR_VERIFICATION`
- `IN_VERIFICATION`
- `OWNER_REVIEW`
- `COMPLETED`
- `BLOCKED`
- `CANCELLED`

## Transition Rules

The implementation lives in `core/task_state_service.py`.

Allowed initial path:

```text
NEW
  -> REQUIREMENTS_DRAFT
  -> READY_FOR_DESIGN
  -> IN_DESIGN
  -> READY_FOR_REVIEW
  -> IN_REVIEW
  -> READY_FOR_VERIFICATION
  -> IN_VERIFICATION
  -> OWNER_REVIEW
  -> COMPLETED
```

Review may send work back:

```text
IN_REVIEW -> REWORK_REQUIRED -> IN_DESIGN
IN_VERIFICATION -> REWORK_REQUIRED -> IN_DESIGN
OWNER_REVIEW -> REWORK_REQUIRED
```

Most active states may move to:

```text
BLOCKED
CANCELLED
```

`COMPLETED` and `CANCELLED` are terminal in Phase 1.

## Fail-Closed Rules

- Unknown states are rejected.
- Unknown transitions are rejected.
- Design, QA and Verification roles cannot move a task to `COMPLETED`.
- A task with unresolved critical/high findings cannot move to `COMPLETED`.
- Every accepted transition records actor, role, timestamp, reason, supporting message/run, artifacts, checks, risks and owner-approval requirement.
