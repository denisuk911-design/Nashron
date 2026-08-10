# Product Roadmap

Source of truth: `docs/product/PRODUCT_NORTH_STAR.md`.

## Current Priorities

1. Realistic and disciplined team chat.
2. Reliable routing and conversation context.
3. Honest claims and evidence.
4. Understandable skill states and qualification.
5. Provider readiness and authentication.
6. Skill packages.
7. Knowledge and standards services.
8. Artifact and QA finding registries.
9. Training management.
10. Controlled multi-agent workflow.
11. Local-system stabilization.
12. Cloud-ready repository interfaces.
13. Server and web version.
14. Skill marketplace and paid specialization packages.

## Near-Term Work

- Expand owner-facing routing diagnostics from `routing_decisions` with per-message details.
- Replace keyword context scoring with semantic/project-aware context retrieval.
- Build GUI flows for importing, editing and approving full `SKILL.md` packages.
- Build source-file import with hashing for knowledge and standards.
- Add evidence detail views with task/run/artifact links.
- Add rework-cycle analytics.

## Recently Implemented With Limitations

- Persistent conversation thread ownership in SQLite.
- Active thread owner included in prompt context snapshots.
- Thread owner diagnostics in Director Console.
- First-class open/answered thread questions with assigned employee and answer-message evidence.
- Relevance-ranked context snapshots instead of broad raw-history prompts.
- Response waiting budgets exposed in Settings with visible warnings, audit events and optional auto-cancel.
- Contextual handoff scheduling now uses the active employee roster and records handoff scheduling events.
- Contextual handoff delivery now records target employee run starts and exposes scheduled/started handoff rate.
- Autonomous loops now require explicit owner intent and single-employee goals stay pinned to the addressed employee.
- Product diagnostics include direct-address delivery rate from persisted routing decisions.
- Basic skill package registry in Director Console: create draft package, activate/suspend and assign to employees without increasing progress falsely.
- Basic knowledge card registry in Director Console: create draft card, manage status, retrieve active cards into prompts and record `knowledge_usage`.
- Basic standard card registry in Director Console: create draft standard, manage status, retrieve active standards into prompts and record `standard_usage`.
- Structured artifact import from valid run JSON with workspace verification, hash/size metadata and missing-file visibility.
- Read-only artifact browser in Director Console with status, validation, run, hash and file-open action.
- Artifact detail view shows related QA findings through task/path matching.
- Persistent artifact-finding links with match type, confidence and audit events.
- Basic QA finding registry in Director Console: create findings, manage review/rework/closure status and count open/blocking/repeated findings.
- Structured agent findings are imported from valid run JSON and deduplicated per run.

## Mid-Term Work

- Implement real skill packages with `SKILL.md`, source material, checklists and qualification tasks.
- Expand knowledge cards with source-file import, source hash calculation, semantic search and applied/ignored/misapplied evidence.
- Expand standards registry with approval workflow, source hashing and compliance evidence.
- Expand artifact and QA finding registries with rework-cycle analytics.
- Add training programs managed through the Director Console.

## Long-Term Direction

- Prepare local repositories for future server APIs.
- Support desktop and web clients.
- Support user accounts, organizations and synchronized projects.
- Support marketplace-style skill packs without weakening local trust and audit rules.
