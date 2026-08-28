from __future__ import annotations

from core.demo_sandbox_service import DemoSandboxService


def test_demo_sandbox_runs_goal_work_review_without_organization_state(tmp_path):
    result = DemoSandboxService(tmp_path / "profile").run()

    assert result.completed
    assert result.workspace == tmp_path / "profile" / "demo_sandbox"
    assert result.work_items == 3
    assert result.artifacts >= 2
    assert result.observations >= 3
    assert result.reviews >= 1
    assert (result.workspace / "checkpoints" / "state.json").is_file()
    assert (result.workspace / "workspace" / "artifacts" / "work_product.md").is_file()
