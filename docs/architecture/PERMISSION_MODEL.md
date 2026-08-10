# Permission Model

Version: 1.0

Prompt instructions are not a substitute for technical permission checks. ROMAN2025 needs explicit permissions stored outside chat text.

## Permission IDs

```text
CHAT
READ_WORKSPACE
WRITE_WORKSPACE
DELETE_FILES
RUN_COMMANDS
MODIFY_PROJECT
CREATE_DOCUMENTS
REVIEW_ARTIFACTS
CREATE_FINDINGS
CLOSE_FINDINGS
MANAGE_SKILLS
MANAGE_KNOWLEDGE
MANAGE_EMPLOYEES
MANAGE_STANDARDS
REQUEST_APPROVAL
GRANT_APPROVAL
ACCESS_INTERNET
ACCESS_EXTERNAL_PATHS
```

## Owner-Only Permissions

```text
MANAGE_EMPLOYEES
GRANT_APPROVAL
MANAGE_STANDARDS
```

Only `ORGANIZATION_OWNER` may grant these in the management foundation.

## Safe Presets

Document Control Officer:

- read workspace;
- create documents;
- update indexes;
- no technical approval;
- no broad deletion.

Learning Coordinator:

- read registered sources;
- create learning queue;
- create draft cards;
- create qualification proposals;
- no active-knowledge approval;
- no standard modification.

QA Engineer:

- read artifacts;
- run review tools;
- create findings;
- no silent design modification;
- no owner approval.

## Phase 1 Implementation

Permissions are stored in `agent_permissions`. Validation lives in `ManagementService`.

## Phase 2A Permission Precedence

Effective permissions are calculated as:

```text
(role inherited permissions + direct grants) - direct denies
```

Phase 2A stores direct grants in `agent_permissions` and direct denies in `agent_permission_denies`.

Owner-only permissions are visible but disabled in the normal GUI:

- `MANAGE_EMPLOYEES`
- `GRANT_APPROVAL`
- `MANAGE_STANDARDS`

The standard employee wizard rejects assigning owner-only permissions to AI employees.
