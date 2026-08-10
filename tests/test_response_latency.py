from core.response_latency import ResponseLatencyPolicy


def test_response_latency_policy_uses_safe_defaults():
    policy = ResponseLatencyPolicy.from_settings({})

    assert policy.soft_warning_seconds == 20
    assert policy.extended_warning_seconds == 90
    assert policy.timeout_seconds == 0
    assert not policy.timeout_enabled


def test_response_latency_policy_orders_thresholds():
    policy = ResponseLatencyPolicy.from_settings(
        {
            "response_soft_warning_seconds": "120",
            "response_extended_warning_seconds": "10",
            "response_timeout_seconds": "30",
        }
    )

    assert policy.soft_warning_seconds == 120
    assert policy.extended_warning_seconds == 121
    assert policy.timeout_seconds == 122
    assert policy.timeout_enabled


def test_response_latency_policy_ignores_bad_values():
    policy = ResponseLatencyPolicy.from_settings(
        {
            "response_soft_warning_seconds": "bad",
            "response_extended_warning_seconds": None,
            "response_timeout_seconds": "0",
        }
    )

    assert policy.soft_warning_seconds == 20
    assert policy.extended_warning_seconds == 90
    assert policy.timeout_seconds == 0
