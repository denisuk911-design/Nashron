# Context Assembly

Agent prompts include three layers:

1. Immediate context: recent relevant chat messages.
2. Task context: active task id, run id and expected response mode.
3. Organizational context: employee role, permissions, team roster and skills.

The prompt includes a compact `CONTEXT SNAPSHOT` so newly created employees receive the current task context instead of only the last owner message.

Current implementation:
- uses `ContextSnapshotService`;
- selects recent relevant messages, not the whole raw chat log;
- ranks context by current message tokens, selected employee, current thread owner and role-specific terms;
- keeps accepted facts and unresolved questions as separate prompt sections;
- unresolved questions are loaded from `thread_questions` when persisted question state exists;
- falls back to the latest messages only when no relevance signal exists.

Limitations:
- relevance is deterministic keyword scoring, not semantic retrieval;
- accepted facts are extracted heuristically;
- unresolved question detection is heuristic at creation time, but open/answered state is persisted after creation;
- task artifacts and findings are not yet fully merged into context selection.
