from runtime_v3.autonomy_policy import AutonomyPolicy
from runtime_v3.models import Action, ActionType


def _write(payload: dict[str, str]) -> Action:
    return Action("action-test", "work-test", "employee-test", ActionType.FILESYSTEM_WRITE, payload)


def test_work_product_content_does_not_trigger_owner_approval() -> None:
    action = _write({
        "path": "v3_provider_output/result.md",
        "content": "The publication is complete; deploy and payment are not requested.",
    })

    assert not AutonomyPolicy.requires_owner_approval(action)


def test_risky_target_still_requires_owner_approval() -> None:
    action = _write({"path": "publish/release.md", "content": "verified"})

    assert AutonomyPolicy.requires_owner_approval(action)
