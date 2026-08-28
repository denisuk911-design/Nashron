import json

from core.beta_health_service import BetaHealthService


def test_health_persists_provider_and_goal_failures_without_secrets(tmp_path):
    service = BetaHealthService(tmp_path)
    service.mark_start()
    service.record_provider_failure("GEMINI_CLI", "AQ.secret-key")
    service.record_goal_failure("failed Goal")
    service.mark_ready()

    restored = BetaHealthService(tmp_path)
    snapshot = restored.snapshot()
    assert snapshot["status"] == "HEALTHY"
    assert snapshot["counts"] == {"provider_failure": 1, "goal_failure": 1}
    assert "AQ.secret-key" not in json.dumps(snapshot, ensure_ascii=False)


def test_health_detects_unclean_previous_start(tmp_path):
    service = BetaHealthService(tmp_path)
    service.mark_start()
    restarted = BetaHealthService(tmp_path)
    restarted.mark_start()
    assert restarted.snapshot()["counts"]["crash"] == 1
