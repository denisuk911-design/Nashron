# Standard Card Registry

Standard cards are owner-controlled requirements. They are stricter than general
knowledge cards because they may define mandatory gates for engineering work.

Implemented entities:

- `standard_cards`: code, title, requirement, scope, source metadata, authority,
  mandatory level, role scope, tags, status, version and review notes.
- `standard_card_events`: append-only audit events.
- `standard_usage`: existing Phase 1 table now records when an active standard
  was supplied to an agent prompt and how the run later accounted for it.

Standard states:

- `DRAFT`
- `NEEDS_REVIEW`
- `ACTIVE`
- `SUSPENDED`
- `CONFLICTING`
- `REJECTED`
- `SUPERSEDED`

Authority vocabulary:

- `OFFICIAL`
- `STANDARD_BODY`
- `MANUFACTURER`
- `INTERNAL`
- `PROJECT`
- `UNVERIFIED`

Mandatory levels:

- `MANDATORY`
- `RECOMMENDED`
- `GUIDANCE`

Director Console behavior:

- owner can add a draft standard;
- owner can activate, suspend or reject a standard;
- active standards are retrieved by deterministic keyword/role matching;
- prompt supply is recorded as `standard_usage` with `usage_type=SUPPLIED`;
- structured responses can record `APPLIED`, `IGNORED` or `MISAPPLIED` for
  standards that were supplied to the same run.
- structured QA findings with `standard_id` record `MISAPPLIED` for that
  standard when the same standard was supplied to the reviewer run.

Trust rules:

- draft/rejected/conflicting standards are not supplied to agents;
- source and authority must be explicit;
- supplying a standard does not prove compliance;
- application evidence is accepted only when the structured response references
  a standard ID that was actually supplied to the same run;
- supplied standards that are not referenced in structured response are recorded
  as `IGNORED` for that run;
- invented standard IDs are rejected and logged.
- standard violations from QA findings are accepted as `MISAPPLIED` evidence
  only when the referenced standard was supplied to the same run.

Known limitations:

- retrieval is keyword-based, not semantic;
- file import and source-hash calculation are not automated yet;
- approval workflow is represented by status changes, not a full owner approval
  wizard yet;
- `APPLIED` currently means the run explicitly accounted for the supplied
  standard in structured evidence; deeper compliance verification remains future
  work.
