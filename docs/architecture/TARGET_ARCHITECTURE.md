# Target Architecture - ROMAN2025

ROMAN2025 should be a standalone engineering multi-agent workspace. The UI remains a working chat, but the authoritative workflow state must live in application services and SQLite, not in natural-language messages.

## Target Layers

```text
GUI
  -> MainWindow
  -> TaskOrchestrator
  -> TaskStateService / AgentRouter / ContextAssembler
  -> SkillService / KnowledgeService / StandardsService / ReferenceDesignService
  -> ArtifactRegistry / FindingRegistry / ApprovalService
  -> ManagementService / ConfigurationRepository
  -> AgentClient implementations
  -> SQLite + workspace files
```

## Logical Roles

- Project Manager: formalizes objective, plan, expected artifacts, blockers and status.
- Design Engineer: creates/modifies engineering artifacts and performs self-checks.
- QA Engineer: independently reviews requirements, artifacts, standards and evidence.
- Verification/Test Engineer: checks reproducibility, tool claims and negative cases.

Roles must not be permanently bound to display names or model providers.

## Phase 1 Foundation

Implemented direction:

- stable task IDs;
- stable run IDs;
- explicit task state vocabulary;
- non-destructive SQLite schema extension;
- `TaskStateService`;
- `TaskOrchestrator` boundary;
- `AgentRouter`;
- common `AgentClient` protocol;
- versioned structured response parser;
- audit table for application workflow events.

## Future Engineering Services

Planned for later phases:

- `ArtifactRegistry`: file metadata, hashes, revisions and claimed-vs-actual changes.
- `FindingRegistry`: structured QA findings with append-only event history.
- `ApprovalService`: owner-reserved actions and design authority boundaries.
- `KnowledgeService`: engineering knowledge cards and book-derived knowledge.
- `StandardsService`: mandatory standards and controlled vocabularies.
- `ReferenceDesignService`: approved prior designs and metadata.

## Director Console

ROMAN2025 also needs an owner-facing Director Console. It manages employees, roles, permissions, skills, training sources, standards, knowledge, reference designs, approvals, audit and system health through explicit UI forms instead of chat commands.

Phase 1 adds only foundations:

- `AgentProfile`;
- `RoleProfile`;
- lifecycle states;
- permission vocabulary;
- management audit events;
- safe configuration repository;
- visible preview entry point named `Команда`.

## Engineering System Layout

```text
Engineering_System/
  standards/
  skills/
    common/
    project_manager/
    design_engineer/
    qa_engineer/
    verification_engineer/
  knowledge/
    active/
    draft/
    conflicts/
    rejected/
    superseded/
  reference_designs/
  books/
  templates/
  projects/
  tasks/
```
