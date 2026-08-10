# Conversation Threads

The application persists the active conversation owner in SQLite and also keeps a working copy in `MainWindow` during runtime.

Thread fields:
- `conversation_thread_id`;
- `active_addressee_agent_id`;
- `active_task_id`;
- `active_topic`;
- `last_user_message_id`;
- `expected_next_actor`;
- `thread_status`;
- `updated_at`.

Current implementation:
- stores thread state through `ConversationThreadService`;
- persists state in `conversation_threads`;
- loads owner keys on application startup;
- uses the persisted owner for continuation routing;
- stores owner questions in `thread_questions` with `OPEN` / `ANSWERED` / `ACCEPTED` state;
- moves a question to `ANSWERED` when the assigned employee produces an answer message;
- lets the owner accept the answer or return the question to `OPEN` from diagnostics;
- includes thread state in the prompt `CONTEXT SNAPSHOT`;
- exposes recent question state in product diagnostics;
- exposes active thread owners in `Команда -> Диагностика`.

A direct exchange remains owned by the addressed employee until the owner addresses someone else, starts a team discussion, requests review, or stops the exchange. Informational broadcasts do not clear the previous owner.

Limitations:
- there is one active thread record per conversation id;
- full semantic answer quality is not yet verified automatically; owner acceptance is the current decision gate;
- handoff records are still task-level, not fully merged with thread ownership.
