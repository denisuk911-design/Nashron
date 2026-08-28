from __future__ import annotations

from tests.test_director_workflow_e2e import _organization
from core.supervisor_application_service import SupervisorApplicationService
from core.supervisor_guide_service import SupervisorGuideService


def test_supervisor_application_service_exposes_guide_director_and_operator(tmp_path):
    database, organization_id = _organization(tmp_path)
    supervisor = SupervisorApplicationService(database)

    before = supervisor.guide(organization_id)
    assert before["mode"] == "GUIDE"
    assert before["state"] == "WAITING_FOR_GOAL"

    plan = supervisor.director(organization_id, "Создать проверяемый файл")
    action = supervisor.operator(plan.plan_id)
    assert action is not None
    assert action.assignment_id
    assert supervisor.get_plan(plan.plan_id).plan_id == plan.plan_id


def test_guide_returns_owner_safe_plan_projection_without_internal_ids(tmp_path):
    database, organization_id = _organization(tmp_path)
    supervisor = SupervisorApplicationService(database)
    plan = supervisor.director(organization_id, "Создать документ")

    projection = supervisor.guide(organization_id, "Создать документ")["plan"]
    assert projection["plan_id"] == plan.plan_id
    assert "director_agent_id" not in projection
    assert all("agent_id" not in item for item in projection["assignments"])


def test_supervisor_guide_persists_familiarity_and_offers_show_or_do(tmp_path):
    state_path = tmp_path / "guide.json"
    actions = []
    guide = SupervisorGuideService(state_path, action_handler=actions.append)

    first = guide.explain("director")
    assert first["suggestion"] == "show"
    assert first["target"] == "director_button"
    guide.mark_seen("director")
    guide.mark_seen("director")
    second = SupervisorGuideService(state_path, action_handler=actions.append).explain("director")
    assert second["familiarity"] == 2
    assert second["suggestion"] == "do"
    done = guide.do("director")
    assert done["ok"]
    assert actions == ["director_button"]
