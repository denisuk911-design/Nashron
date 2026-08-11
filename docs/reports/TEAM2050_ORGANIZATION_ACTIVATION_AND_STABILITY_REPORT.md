# Team2050 Organization Activation and Stability Report

Status: `IMPLEMENTED_WITH_LIMITATIONS`

## Stop bug

Root cause: the GUI kept a cancelled `GenerateWorker` object while the provider
process was terminating. A message arriving in that short window was treated as
live guidance and was not assigned to a new run.

Fix:

- cancellation is tracked separately from normal live guidance;
- a message received while cancellation is finishing is stored as a queued user
  message;
- the queue is released only after the cancelled worker emits its result;
- the next run gets a fresh worker/provider request and therefore a fresh
  provider cancellation state;
- legacy route-only runs remain compatible.

Regression coverage includes cancellation queue recovery and the existing
Codex/Gemini worker and orchestration tests.

## Unicode bug

Root cause: portions of the Director Console source contained CP1251/UTF-8
mojibake while the rest of the application was valid UTF-8.

Fix:

- repaired the affected GUI source strings instead of replacing them with
  English;
- added RU/UA/EN smoke labels for Organization, Employees, Professions, Skills,
  Learning, Templates and Settings;
- added a runtime catalog validator and automated smoke tests;
- logging is UTF-8 and the PyInstaller entry point validates the bundled
  localization catalog at startup.

## Organization before and after

Before, creating an organization or template inserted rows but did not create a
workspace, employees, provider state or routing boundary.

Now `activate_template` performs:

```text
template -> organization instance -> departments -> employee profiles
         -> roles/professions/responsibilities -> provider assignment state
         -> workflow link -> workspace -> active organization -> READY
```

An employee with `UNAVAILABLE` provider is real organizationally but is shown as
`Требуется AI-движок` and is not silently executed. A selected provider can be
Codex, Gemini, Claude or assigned later. Existing employees can also be selected
by the activation service.

The active organization now limits chat roster/routing to its members. Direct
addressing remains supported, and a team call still selects the active roster.

## Preset library

The catalog is data-driven and includes functional, projectized, matrix, flat
and cross-functional management models; RACI, Creator-Reviewer-Approver and
Kanban overlay responsibility/work models; and organization templates including
Scrum software, software product, engineering product, research, consulting,
document production, creative, culinary brigade, learning, small business,
solo professional, advisory board, incident command style and operations
support. Presets carry purpose, size, source/rationale, limitations and review or
research flags.

Scrum is represented by accountabilities, not a manager hierarchy. Kanban is a
workflow overlay, not an organization hierarchy. Matrix manager relations are
available as member data fields but complex matrix execution is not claimed.

## Generic engine proof

Software and culinary presets use the same `OrganizationTemplate`,
`ManagementModel`, `OrganizationMember`, `WorkflowDefinition` and activation
service. No PCB-specific branch is required by the generic engine.

## Tests and build

- Full regression suite: `220 passed` at the latest verification point.
- Unicode and activation tests pass independently.
- EXE build: PASS; packaged process stayed alive through an 8-second smoke run.

## Limitations

- Provider provisioning is explicit; the application does not silently install
  missing CLIs or credentials.
- Organization dashboard is a compact operational view, not a full graph editor.
- RACI/Kanban data foundations exist; full workflow enforcement and complex
  matrix scheduling remain later work.
- Autonomous learning and skill qualification still require evidence-backed
  later phases.

## Manual user test

1. Open the Director Console and choose Organization.
2. Search for `CULINARY_BRIGADE`, choose Create team from preset.
3. Select MINI/STANDARD and assign providers or leave one as Assign later.
4. Confirm that the wizard creates organization, employees, departments and a
   workspace, and that the dashboard shows missing providers explicitly.
5. Open the chat and send a direct request to a provider-ready employee.
6. Start a generation, press Stop, then immediately send a new message.
7. Switch RU, UA and EN and verify the required labels contain no mojibake.

The next large Agent Runtime phase is intentionally not started by this report.
