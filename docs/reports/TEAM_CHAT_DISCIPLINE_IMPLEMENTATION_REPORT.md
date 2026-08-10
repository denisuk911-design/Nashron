# Team Chat Discipline Implementation Report

Status: `IMPLEMENTED_WITH_LIMITATIONS / READY_FOR_USER_TEST`

North Star reference: `docs/product/PRODUCT_NORTH_STAR.md`

Implemented:
- deterministic participation modes in `core/team_routing.py`;
- single-responder default;
- direct-name and alias routing;
- contextual handoff scheduling by current active employee roster, including newly added employees;
- ordinary addressed work commands no longer start autonomous multi-agent loops by default;
- explicit autonomous goals addressed to one employee stay pinned to that employee unless a handoff is produced;
- continuation routing to the active addressee;
- broadcast/no-response routing;
- manual chat controls for recipient and mode;
- routing decision persistence in SQLite;
- contextual handoff start events in SQLite;
- no-impersonation enforcement for multi-speaker provider output;
- claim/evidence validation for unsupported completion claims;
- skill lifecycle display in Director Console;
- owner-managed skill package registry with package status, audit events and employee assignment;
- owner-managed knowledge card registry with source authority, status, audit events and prompt-supply usage;
- owner-managed standard card registry with requirement text, mandatory level, source metadata, audit events and prompt-supply usage;
- structured artifact registry import for created, modified and deleted files with workspace path checks and SHA-256 evidence;
- read-only artifact browser in Director Console with status, validation, run, hash and file-open action;
- artifact browser shows related QA findings by normalized path and task;
- persistent artifact-finding link records with match type, confidence and audit events;
- structured QA finding registry with severity, confidence, standard link, repeat key, status and audit events;
- automatic import of valid structured agent `findings` into the QA finding registry with per-run duplicate suppression;
- prompt envelope fields for participation, claims, evidence and skills used;
- response status stages in worker UI;
- local product quality metrics in Director Console;
- direct-address delivery metric computed from persisted routing decisions;
- handoff delivery metric computed from scheduled and actually started contextual handoff events;
- response-latency warnings and optional auto-cancel controlled from Settings;
- owner-readable routing diagnostics showing mode, selected responders, exclusions and reason;
- persistent conversation-thread owner state with prompt snapshot and diagnostics view;
- first-class thread questions with open/answered/accepted state, assigned employees and answer-message evidence;
- owner-readable thread question diagnostics showing question text, status, assignee and answer-message link;
- owner actions to accept an answer or return the question to work from diagnostics;
- relevance-ranked context snapshots replacing broad raw-history prompt blocks;
- automated tests for routing, evidence and skill progress.

Limitations before final completion:
- manual user testing is still required;
- only one active thread record is maintained per conversation;
- automatic semantic answer-quality verification is still future work; owner acceptance is the current decision gate;
- context relevance uses deterministic keyword scoring, not semantic retrieval;
- latency budgets are global for all agents and task types; task-specific budgets are future work.
- skill package editing/import/export and dedicated approval wizards are still future work.
- knowledge and standard retrieval are keyword/role based; full source import and semantic retrieval are still future work.
- rework-cycle analytics are still future work.

## NORTH STAR IMPACT

Teamwork impact:
- direct addressing, continuation ownership and team-discussion limits reduce uncontrolled parallel replies;
- handoffs now target named active employees from the current roster instead of being limited to the original Roman/Petr pair;
- handoffs are now measured as scheduled vs started, so a promised handoff is visible if it never reaches the target employee;
- no-impersonation enforcement keeps employees inside role boundaries.
- thread ownership now survives restart and keeps short follow-ups attached to the responsible employee.
- unresolved owner questions remain visible in persisted thread state and context snapshots until the assigned employee answers, and the owner can return weak answers to work.
- new employees receive selected relevant context instead of an unfiltered chat dump.

Skills/knowledge quality impact:
- unsupported claims no longer update skills;
- skill UI now shows lifecycle, evidence summary, next step and confidence instead of treating one percentage as truth.
- skill packages and employee assignments are separate from qualification, so created skills no longer imply learned skills.
- active knowledge cards can be supplied to agents and usage is recorded; drafts and rejected cards are not supplied.
- active standards can be supplied to agents and usage is recorded; supplying a standard does not yet prove compliance.
- unresolved HIGH/CRITICAL findings block task completion and are visible as structured review evidence.

No-code management impact:
- chat recipient and participation mode controls are available in the interface;
- skill state inspection is available in Director Console.
- basic skill package creation, activation, suspension and assignment are available in Director Console.
- basic knowledge card creation and status management are available in Director Console.
- basic standard creation, activation, suspension and rejection are available in Director Console.
- basic QA finding creation, status management and audit inspection are available in Director Console.
- quality diagnostics are available in Director Console without reading SQLite or logs.

Trust impact:
- routing decisions are persisted for audit;
- explicit addressed-recipient delivery is measured from saved routing evidence;
- contextual handoff delivery is measured from saved app events, not from employee claims;
- completion claims are checked against structured evidence;
- raw provider output remains preserved in run records.
- duplicate suppression, unsupported claims, impersonation attempts and evidence-backed runs are counted locally.
- long-response warnings and auto-cancel events are counted locally.
- active/used knowledge card counts are visible in product diagnostics.
- active/used standard counts are visible in product diagnostics.
- verified/missing artifact counts are visible in product diagnostics.
- artifact registry is inspectable from the interface without SQLite access.
- findings can be inspected from the artifact detail view without searching another table first.
- artifact-to-finding relationships are stored as durable auditable records, not only recomputed for display.
- open/blocking/repeated finding counts are visible in product diagnostics.
- open/answered/accepted thread question counts are visible in product diagnostics.
- concrete thread questions are inspectable in product diagnostics without reading SQLite.
- provider review output can now create structured QA evidence without exposing JSON in chat.

User-experience impact:
- ordinary messages default to fewer responders;
- slow responses show system status stages;
- slow responses now show application-owned waiting warnings, not invented employee text;
- the owner can cancel active work.
- diagnostics show active thread owner so the owner can understand who currently owns the exchange.
