# Artifact Registry

Artifacts are files or work products claimed by an agent run. They are tracked
separately from chat messages and raw provider JSON.

Implemented entities:

- `artifacts`: task, project, relative path, type, authoring role, run, current
  hash, size, status and validation status.
- `artifact_revisions`: immutable observed revisions with hash, size, run and
  metadata.
- `artifact_finding_links`: persistent task/path links between artifacts and QA
  findings with match type, confidence and active status.
- `artifact_finding_link_events`: append-only audit records for link creation and
  updates.

Structured-response import:

- valid `files_created`, `files_modified` and `files_deleted` entries are
  imported after a successful agent run;
- paths are resolved inside the active workspace;
- existing files are hashed with SHA-256 and marked `OBSERVED / VERIFIED`;
- missing created or modified files are marked `MISSING / NOT_FOUND`;
- deleted files are marked `DELETED / VERIFIED_ABSENT` only when absent;
- paths outside the workspace are recorded as `MISSING / UNSAFE_PATH`.

Trust rules:

- a provider claim is not enough to prove work;
- a file claim becomes verified evidence only when the application observes the
  file and records hash/size metadata;
- missing artifacts remain visible instead of being silently ignored;
- invalid structured responses do not import artifacts.

Current limitations:

- Director Console has a read-only artifact browser with details and file open action;
- artifacts are reconciled with QA findings by task and normalized affected artifact path;
- rework-cycle analytics still come later.

Finding links:

- artifact details show related QA findings, severity, status, required action,
  link match type and link confidence;
- exact workspace-relative paths are preferred;
- filename-only findings are matched as a compatibility fallback for older records;
- repeated reconciliation is idempotent and does not create duplicate links.
