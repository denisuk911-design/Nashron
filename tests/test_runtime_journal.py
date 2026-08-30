from core.runtime_contracts import ExecutionPolicy, ExecutionRequest, ExecutionResult
from core.runtime_journal import RuntimeExecutionJournal


def test_journal_recovers_completed_result_after_restart(tmp_path):
    journal = RuntimeExecutionJournal(tmp_path)
    request = ExecutionRequest("org-a", "task", ExecutionPolicy.MANAGED_AGENT, correlation_id="run-1")
    journal.begin(request)
    journal.complete(request, ExecutionResult(True, "org-a", "langgraph", "done", "run-1", artifact_refs=("a-1",)))
    restarted = RuntimeExecutionJournal(tmp_path)
    record = restarted.recover("org-a", "run-1")
    assert record is not None
    assert record.status == "COMPLETED"
    assert record.runtime_id == "langgraph"
    assert record.artifact_refs == ("a-1",)


def test_journal_does_not_cross_organization_scope(tmp_path):
    journal = RuntimeExecutionJournal(tmp_path)
    request = ExecutionRequest("org-a", "task", ExecutionPolicy.MANAGED_AGENT, correlation_id="run-1")
    journal.complete(request, ExecutionResult(True, "org-a", "native", "done", "run-1"))
    assert journal.recover("org-b", "run-1") is None
