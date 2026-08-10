# Finding Registry

Findings are structured QA/review issues. They are not ordinary chat messages.

Implemented entities:

- `findings`: task, severity, confidence, affected artifact, location, evidence,
  standard link, status, resolution and repeat key.
- `finding_events`: append-only audit events.

Finding statuses:

- `OPEN`
- `IN_REWORK`
- `READY_FOR_RECHECK`
- `RESOLVED`
- `ACCEPTED_RISK`
- `REJECTED`
- `DEFERRED`

Severity:

- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

Director Console behavior:

- owner can create a finding for an existing task;
- owner can move it to rework, recheck, resolved, accepted risk or rejected;
- finding details and audit history are visible;
- valid agent structured-response `findings` are imported into the registry after
  a successful run;
- HIGH/CRITICAL unresolved findings remain blocking for task completion through
  the existing `task_has_blocking_findings` rule.
- imported structured findings that reference a supplied `standard_id` are also
  recorded as `MISAPPLIED` standard usage for that reviewer run.

Quality metrics:

- open findings;
- blocking findings;
- repeated findings by `repeat_key`.

Trust rules:

- a chat statement does not close a finding;
- imported findings are idempotent per `run_id` and repeat key;
- resolved/accepted/rejected findings require an explicit status change;
- standard compliance is not proven by supplying a standard to a prompt;
- compliance must be shown by checks, review evidence and closed findings.
- a finding cannot create standard usage for a standard that was not supplied to
  the same run.

Known limitations:

- malformed structured responses and empty findings are ignored safely;
- artifact registry links findings to artifacts by task/path matching;
- rework-cycle counting is based on finding events in a later phase.
