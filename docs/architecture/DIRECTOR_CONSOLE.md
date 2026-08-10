# Director Console

Phase: Phase 2A working slice implemented.

The Director Console is the owner-facing management center for ROMAN2025. It must not be implemented as ordinary chat commands. Management actions use explicit forms, validation, previews, confirmations, audit records and safe persistence.

## Owner Role

Permanent authority role:

```text
ORGANIZATION_OWNER
```

The owner may create/deactivate agents, assign roles, configure permissions, approve standards, approve active knowledge, accept risks, view audit records and stop autonomous workflows. Agents cannot grant themselves owner authority.

## Entry Point

Current UI adds a visible top-bar button:

```text
Команда
```

It opens a separate Director Console dialog. The console is not embedded inside the main chat.

## Target Pages

```text
Команда / Director Console
  Overview
  Employees
  Roles
  Skills
  Training
  Knowledge
  Standards
  Reference Designs
  Projects and Tasks
  Permissions
  Approvals
  Audit Log
  System Health
```

## Implemented Pages In Phase 2A

- `Обзор`: compact cards for lifecycle counts, roles, provider availability, configuration warnings, database/repository health and recent actions.
- `Сотрудники`: filtered table, detail view, add/edit/suspend/reactivate/archive actions.
- `Роли`: read-first role table with responsibilities, restrictions and assigned employees.
- `Права`: per-employee inherited/direct/effective permission view.
- `ИИ и CLI`: provider installation/auth/access/health/capability status view.
- `Журнал действий`: read-only management audit table with text filtering.

## Add Employee Wizard Wireframe

```text
Step 1 - Basic identity
  display name
  generated stable agent ID
  description
  avatar
  lifecycle state

Step 2 - Organizational role
  PROJECT_MANAGER / DESIGN_ENGINEER / QA_ENGINEER / ...

Step 3 - Provider and backend
  Codex CLI / Gemini CLI / future provider / unavailable

Step 4 - Responsibilities
  primary objectives
  allowed activities
  prohibited activities
  required outputs
  escalation conditions
  reporting destination
  permitted project scope

Step 5 - Skills
  select existing skills only

Step 6 - Knowledge access
  active/draft knowledge, standards, books, reference designs, project docs

Step 7 - File and tool permissions
  read/write workspace, run commands, KiCad, internet, approvals, etc.

Step 8 - Review and confirmation
  preview employee, role, provider, permissions, skills, risks
```

Implemented in Phase 2A as `AddEmployeeWizard`.

## Safe Creation Pattern

All management objects should use:

1. select object type;
2. fill structured fields;
3. validate;
4. preview files and database records;
5. show permission and workflow impact;
6. explicit owner confirmation;
7. transactional write;
8. audit result.

## Failure Handling

- Validation failure prevents persistence.
- Dry run performs validation only.
- Database writes use transactions.
- Configuration files use temporary files and atomic replacement.
- Partial mandatory failure must report rollback state.
- Management audit records are append-only from the UI perspective.

## Transaction Strategy

Employee creation writes the JSON profile first through atomic replacement, then writes SQLite rows in a transaction. If the database write fails, the JSON profile is removed as compensating rollback.

Employee edit stores the previous JSON payload, writes the new JSON atomically, applies SQLite updates, and restores the previous JSON if the database update fails.

Dry-run validation returns the planned database rows and files without creating persistent state.

## Later Implementation Slices

Phase 2A:

Implemented.

Phase 2B:

- skill management UI.

Phase 2C:

- training and knowledge management UI.

Phase 2D:

- document control and learning coordinator workflows.

Phase 2E:

- export/import, health dashboard and advanced audit.

## Future Tests

- create employee successfully;
- duplicate employee ID rejected;
- unavailable provider rejected;
- unsafe role conflict detected;
- owner confirmation required;
- suspended employee receives no new tasks;
- archived employee history preserved;
- permanent deletion does not remove task history;
- audit event always created;
- dry run makes no persistent changes.
