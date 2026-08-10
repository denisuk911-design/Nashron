# Structured Agent Response Schema

Version: 1.0

Agents should return:

1. a short human-readable reply;
2. a fenced JSON object for audit and future workflow routing.

Example:

```json
{
  "schema_version": "1.0",
  "agent_id": "agent-roman",
  "role": "DESIGN_ENGINEER",
  "task_id": "TASK-...",
  "run_id": "RUN-...",
  "action": "HANDOFF",
  "proposed_state": "READY_FOR_REVIEW",
  "summary": "Prepared design artifacts for review.",
  "files_read": [],
  "files_created": [],
  "files_modified": [],
  "files_deleted": [],
  "checks": [
    {
      "name": "ERC",
      "status": "TOOL_EXECUTED",
      "result": "PASS",
      "evidence_path": "reports/erc.txt"
    }
  ],
  "findings": [],
  "risks": [],
  "knowledge_used": [
    {
      "knowledge_id": "KNOW-...",
      "outcome": "APPLIED",
      "reason": "Used this rule to decide the release gate.",
      "evidence_ids": []
    }
  ],
  "standards_used": [
    {
      "standard_id": "STD-...",
      "outcome": "APPLIED",
      "reason": "Checked this mandatory requirement.",
      "evidence_ids": []
    }
  ],
  "handoff_to_role": "QA_ENGINEER",
  "owner_action_required": false
}
```

## Phase 1 Behavior

- Parser: `core/structured_response.py`.
- Required fields are validated.
- Human text is preserved for display.
- Raw structured text is preserved in `agent_runs.raw_response`.
- Valid JSON is stored in `agent_runs.parsed_response`.
- Parse errors are stored in `agent_runs.parse_errors`.
- Missing or malformed structured responses do not trigger task transitions.
- `ResponseCleaner` may clean display text, but it is not the audit source.
- Valid `files_created`, `files_modified` and `files_deleted` entries are
  imported into the Artifact Registry and checked against the workspace.
- Valid `findings` entries are imported into the Finding Registry.
- Valid `knowledge_used` and `standards_used` entries are recorded only when
  the referenced card was supplied to the same run.
- Supplied knowledge/standard cards that are not referenced by the structured
  response are recorded as `IGNORED` for that run.
- Allowed usage outcomes are `APPLIED`, `IGNORED` and `MISAPPLIED`.
