# Migration Plan

## Phase 0 - Architecture Audit

Status: done.

- inspected repository structure;
- identified PySide6 GUI and `app.py` entry point;
- identified `MainWindow` as the current mixed GUI/workflow coordinator;
- identified current SQLite schema and message-history compatibility requirement;
- identified current Codex/Gemini client shape;
- documented current risks and target direction.

## Phase 1 - Foundations

Status: implemented with limitations.

Added:

- task/run/audit persistence tables;
- management profile/role/permission persistence tables;
- state machine vocabulary and validation service;
- initial orchestration boundary;
- initial Director Console foundation and preview entry point;
- provider-independent client protocol;
- role routing boundary;
- structured response parser;
- prompt instruction for human reply plus JSON audit envelope;
- tests for state transitions, structured response parsing, migration and run audit.

Preserved:

- existing Roman/Petr chat behavior;
- current message history;
- current settings and workspace logic;
- current CLI providers;
- current GUI framework.

## Phase 2 - Artifact And Finding Control

Do not execute without new user instruction.

## Phase 2A - Director Console First Slice

Status: implemented with limitations.

Planned:

- organization dashboard;
- employee list;
- add employee wizard;
- suspend/reactivate employee;
- role and permission preview;
- management audit log.

Implemented:

- separate console window;
- overview, employee list/detail, roles, permissions and audit tabs;
- add employee wizard;
- edit employee dialog;
- lifecycle actions with reason;
- provider status checks through existing clients;
- dry-run preview;
- service tests and GUI smoke tests.

## Phase 2A.1 - Provider Readiness Visibility

Status: implemented with limitations.

Implemented:

- provider registry;
- provider profile model;
- provider lifecycle states;
- lightweight detection for current Codex/Gemini integrations;
- non-ready Claude provider definition;
- provider health metadata;
- employee execution readiness calculation;
- Director Console tab `ИИ и CLI`;
- provider assignment records for Roman/Petr.

Deferred:

- automatic CLI installation;
- authentication launch UI;
- bounded model capability probes;
- first-run setup wizard;
- Claude execution adapter.

Planned:

- workspace before/after hashing;
- first-class artifact registry UI;
- structured QA finding registry;
- handoff records;
- owner approval request UI.

## Phase 3 - Context And Engineering Services

Do not execute without new user instruction.

Planned:

- `KnowledgeService`;
- `StandardsService`;
- `ReferenceDesignService`;
- role-specific context retrieval;
- usage traceability.

## Phase 4 - Controlled Engineering Workflow

Do not execute without new user instruction.

Planned:

- Project Manager / Design / QA / Verification role modes;
- bounded review-rework cycles;
- qualification workflow;
- migration of external engineering standards, skills and knowledge.

## Rollback

Phase 1 does not delete existing user data. Before creating the Phase 1 tables, the database creates a sibling backup named:

```text
<database-name>.before_phase1.sqlite3
```

To roll back manually, close the application, replace the active database with that backup, and run the previous build.
