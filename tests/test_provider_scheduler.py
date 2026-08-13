from core.provider_scheduler import ProviderScheduler
from core.send_pipeline_trace import SendPipelineTrace


def test_scheduler_limits_total_and_per_provider(monkeypatch):
    scheduler = ProviderScheduler({"CODEX_CLI": 1, "GEMINI_CLI": 2}, total_limit=3)
    monkeypatch.setattr(scheduler, "_effective_total_limit", lambda: 3)
    scheduler.enqueue("roman", "CODEX_CLI")
    scheduler.enqueue("anna", "CODEX_CLI")
    scheduler.enqueue("petr", "GEMINI_CLI")
    scheduler.enqueue("olena", "GEMINI_CLI")

    started = scheduler.startable()

    assert [run.agent_key for run in started] == ["roman", "petr", "olena"]
    assert scheduler.has_pending
    scheduler.complete("roman")
    assert [run.agent_key for run in scheduler.startable()] == ["anna"]


def test_scheduler_deduplicates_agent_runs():
    scheduler = ProviderScheduler(total_limit=2)
    assert scheduler.enqueue("roman", "CODEX_CLI")
    assert not scheduler.enqueue("roman", "CODEX_CLI")


def test_send_trace_exposes_bubble_latency_budget():
    trace = SendPipelineTrace()
    trace.mark("send_clicked")
    trace.mark("bubble_created")

    payload = trace.payload()

    assert payload["bubble_budget_ok"] is True
    assert payload["stages_ms"]["bubble_created"] <= 50
