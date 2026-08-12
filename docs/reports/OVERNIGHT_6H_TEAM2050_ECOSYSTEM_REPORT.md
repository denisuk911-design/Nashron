# Team2050 Overnight Ecosystem Report

Date: 2026-08-13  
Packaged build: `v2.4.2`, code commit `b6d06ff`  
Final status: `IMPLEMENTED_WITH_LIMITATIONS`

## 1. Executive Summary

The product now starts as a universal organization client rather than a fixed cast of employees. A clean profile contains no organizations and no employees, offers onboarding, can activate a localized team preset without restart, and gives every generated employee a persistent profile, provider assignment, role, biography, avatar and organization membership.

The existing user profile was tested through a consistent SQLite backup. The packaged client opened it, repaired four legacy orphan routing diagnostics, preserved two organizations and ten employees, and finished with a clean integrity and foreign-key check.

Chat UX now has measured message bubbles, smooth wheel and output scrolling, dynamic bottom-follow state, a new-message indicator, selectable multi-message transcripts, localized controls, nine visual themes, custom wallpapers, native theme-aware Windows chrome and configurable original notification sounds.

Evidence-backed experience and director planning foundations are persistent and covered by tests. The full autonomous Director and Learning Manager execution loops are not yet complete; they are explicitly listed as limitations below.

## 2. What Was Broken

- Legacy databases could fail during provider assignment bootstrap with `FOREIGN KEY constraint failed`.
- Product startup and routing still depended on preconfigured employee identities.
- Clean install behavior created or assumed employees instead of representing an empty organization system.
- A newly activated organization was not always visible until restart.
- Message output could duplicate speech, expose structured JSON, clip text or pull the reader to the bottom.
- Theme styling was incomplete in dialogs and lacked a centralized definition.
- Skill growth could be inferred from agent speech instead of persisted work evidence.
- Organization goals had no persistent director-owned plan and assignment model.
- The build path still used old product-named PyInstaller specs.

## 3. What Was Fixed

- Repaired startup ordering, legacy schema references, provider assignments and routing diagnostics.
- Removed production bootstrap and fallback dependencies on predefined employees.
- Added first-run empty state, onboarding, localized template selection and live activation.
- Added data-driven organization presets and generated employee identities.
- Stabilized social/work routing, contextual handoffs, duplicate suppression and structured-output filtering.
- Added evidence-backed experience records, a learning queue and skill-usage deduplication.
- Added persistent director plans, specialist assignments, review assignments and approval boundaries.
- Reworked chat sizing, scrolling, visual themes, background handling and packaging.

## 4. Database/Migrations

Database initialization keeps `PRAGMA foreign_keys = ON`. Before a known integrity repair it creates a timestamped SQLite backup. The current migration path repairs renamed message references and deletes only routing diagnostics whose referenced message no longer exists.

New persistent tables include `experience_records`, `learning_queue`, `project_plans` and `work_assignments`. All schema changes are idempotent under repeated initialization.

Packaged legacy result:

```text
Before startup: 4 routing_decisions foreign-key violations
After startup:  integrity=ok, foreign_keys=0
Organizations:  2 preserved
Employees:      10 preserved
```

## 5. Provider Runtime

The provider catalog contains Codex CLI, Gemini CLI and Claude CLI profiles. Only implemented adapters are exposed as runnable integrations. Provider assignments are stored per employee; startup tolerates unassigned legacy employees and reports readiness rather than crashing.

Agent runs persist provider, task, status, output and evidence. Technical process output is cleaned before speech is displayed. Provider failures become localized system messages and do not masquerade as employee replies.

## 6. Legacy Hero Removal

There are no production seed employees, fixed chat participants, provider fallbacks or routing defaults for former built-in personalities. The only direct legacy employee IDs remaining in production code form an explicit migration guard in `ManagementService`; they are not created or selected by runtime logic.

Clean profile proof:

```text
Organizations: 0
Employees:     0
```

## 7. Organizations

Organizations have isolated conversations, workspaces, departments, members and active/archive lifecycle. Switching the active organization refreshes the conversation and roster. Creation from a preset activates the organization in the current `MainWindow` without restart. Empty organizations and clean install remain valid states.

Permanent deletion is allowed only by the lifecycle rules. Empty organizations and employees without retained work history can be deleted; protected historical records remain archivable.

## 8. Preset Catalog

There are 52 built-in organization presets. They cover software, engineering, PCB/embedded work, quality, documentation, security, data, operations, learning, creative work, support, procurement, culinary workflows and general organizational forms.

Templates persist composition, roles, workflow steps, source metadata and limitations. Activation creates organization data and employees; it does not rely on GUI hardcoding.

## 9. Localization

The interface supports Russian, Ukrainian and English. Core UI text catalogs contain 119 entries per language. Permission, readiness, status and workflow values have localized labels. All 52 preset names have Russian and Ukrainian labels; generated fallback purposes are also localized instead of exposing enum-style identifiers.

Some deep diagnostic and newly expanded management metadata still require a complete string-extraction pass. This is a known limitation, not a claim of 100% localization.

## 10. Employee Generator

Preset activation creates locale-aware names, short biographies, neutral personas and unique avatars. Names use Ukrainian and international pools and remain editable. Profession and personality are stored separately. Generated employees are immediately attached to their organization and visible to the chat router.

## 11. Avatars

The packaged resource directory contains 102 PNG files. The selectable catalog exposes 96 individual avatars and filters out six source/contact sheets. The library includes realistic and illustrated people plus original playful pet/reaction options. User and employee custom avatar paths remain supported.

## 12. Chat UX

- Message rows measure actual wrapped text and keep only a 4-12 px layout reserve.
- Composer starts at 52 px and grows up to 220 px.
- Scroll follow is based on actual distance from the scrollbar maximum with a 32 px threshold.
- Wheel, scrollbar drag, PageUp/PageDown, Home/End and programmatic append are distinguished.
- Reading history is not interrupted by incoming messages or resize.
- Returning manually to the bottom restores live following.
- A localized `New messages` control restores follow explicitly.
- Output and wheel scrolling use bounded easing animations.
- Multi-message selection keeps author, role and timestamp in copied text.
- A 500-message widget test completes append, resize and subsequent append without failure.

## 13. Sounds/Themes

Nine themes are available: Space/Dark, Light, Graphite, Ocean, Forest, Engineering Workshop, Night City, Warm Paper and Minimal. Themes define palette, bubbles, surfaces, input, accent, scrollbar, procedural pattern and native chrome colors. Core text contrast is regression-tested at WCAG AAA ratio (7:1) or better on primary surfaces.

Custom backgrounds support cover, tile and center modes, adjustable opacity and a contrast overlay. Invalid images fall back to the theme color.

Send and receive sounds are original locally synthesized WAV signals. Settings include master enable, direction-specific switches and volume. Receive sound is debounced over 450 ms for burst replies. Loaded history does not produce sounds.

The application uses hybrid native Windows chrome tinted through DWM. This preserves native resize, snap, maximize, taskbar and multi-monitor behavior instead of replacing them with a fragile frameless implementation.

## 14. Director

`DirectorService` requires an explicitly assigned Director/Project Manager/Organization Manager. It creates a persistent plan, assigns specialists, creates a separate reviewer assignment, records acceptance criteria and reports missing roles. The director is never assigned as the specialist who performs every task.

Paid installation, destructive work and permission-sensitive goals enter `AWAITING_OWNER_APPROVAL`. Plans are visible in the Director Console.

Limitation: chat goals do not yet drive the complete plan -> agent run -> review -> rework -> owner report state machine automatically.

## 15. Learning Manager

The Development tab exposes verified experience and the learning queue. Findings create `PROPOSED` learning items; moving an item to `VERIFIED` requires evidence.

Limitation: an autonomous Learning Manager that searches sources, assigns practice, compares before/after quality and requalifies employees is not implemented end to end.

## 16. Skills/Knowledge/Experience

Experience is created only for a successful, non-cancelled run with persisted work evidence such as an artifact, finding or tool result. Social speech alone does not increase experience. Skill usage is deduplicated by run, employee and skill. The system links run evidence, modified files, findings and lessons to each experience record.

Existing skill packages, knowledge cards, standards, findings and artifact registries remain available. Maturity states support draft, practice, review, verified and mature progression, but advancement requires evidence.

## 17. Tests

```text
Full suite: 271 passed
Duration:   111.47 seconds
UX subset:  34 passed after sound integration
```

Coverage includes database repair, startup, clean onboarding, live organization activation, lifecycle, routing, provider provisioning, response cleaning, chat streaming, autoscroll A-F, 500-message load, themes, sounds, director planning and learning evidence.

## 18. Packaged EXE Tests

The current package was built by PyInstaller 6.21.0 from `Team2050.spec`:

```text
dist\Team2050\Team2050.exe
Version:   2.4.2
Commit:    b6d06ff
Build UTC: 2026-08-12T22:27:29.0943145Z
```

Clean packaged profile stayed alive after startup and produced:

```text
integrity=ok, foreign_keys=0, organizations=0, employees=0, templates=52
```

Legacy packaged profile stayed alive after startup and produced:

```text
integrity=ok, foreign_keys=0, organizations=2, employees=10
```

The single-instance lock was exercised with two launches against one isolated profile; the second process remained in the existing-instance notification path. Full manual Windows Snap, mixed-DPI and live-provider message testing cannot be proven by headless automation and remains a user-test item.

## 19. Remaining Limitations

- Full autonomous Director execution and review/rework cycle is not wired to chat goals.
- Full autonomous Learning Manager, web research, learning material ingestion and before/after qualification are not implemented.
- Live multi-provider conversation depends on the user's actual CLI authorization and quotas and was not executed headlessly.
- A final manual packaged UX pass is still needed for Windows Snap, 100/125/150% mixed DPI, multiple monitors, theme switching and audible volume preference.
- Deep management/diagnostic localization still has gaps even though normal chat, onboarding and core management labels are localized.
- The profile directory remains `%LOCALAPPDATA%\Roman2050` for backward compatibility; this is an internal path only.

## 20. Next Recommended Phase

Implement one persistent orchestration state machine that consumes a Director plan, starts assigned agent runs, blocks completion on reviewer evidence, returns findings for rework and emits a concise owner report. Then connect Learning Manager queue items to source ingestion, supervised practice and evidence-based requalification. Add a deterministic fake-provider packaged harness so full Golden Chat and Director/Learning flows can be tested without external quota or credentials.

## Final Dashboard

```text
Tests passed: 271
Built-in presets: 52
Localized presets: 52 RU + 52 UK labels
Localized roles: 8 core role labels per language; generic roles use readable fallback
Avatar count: 96 selectable / 102 packaged PNG
Legacy core hero references: 0 runtime dependencies; 1 explicit migration guard

Organizations clean-test: PASS
Live create without restart: PASS
Permanent delete: PASS
Provider multi-agent test: PASS (routing/assignment regression); live external-provider run not automated
Golden Chat: PASS (automated social/work/routing regressions); live provider dialogue not automated
Packaged startup legacy DB: PASS
Packaged startup clean DB: PASS
Director E2E: FAIL (persistent planning foundation passes; autonomous execution loop missing)
Learning E2E: FAIL (evidence foundation passes; autonomous learning loop missing)

Final status: IMPLEMENTED_WITH_LIMITATIONS
```
