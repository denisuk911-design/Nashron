from types import SimpleNamespace

from core.supervisor_chat_service import SupervisorChatApplicationService


class FakeSupervisor:
    def __init__(self):
        self.calls = []

    def list_plans(self, organization_id=None):
        self.calls.append(("list", organization_id))
        return []


class FakeUniversal:
    def create_organization(self, name):
        return SimpleNamespace(name=name, organization_id="org-new")

    def list_templates(self):
        return [SimpleNamespace(template_id="tpl", name="Engineering team")]

    def activate_template(self, template_id, name):
        return SimpleNamespace(organization=SimpleNamespace(name=name, organization_id="org-team"), employee_ids=("agent-one",))


class FakeManagement:
    def __init__(self):
        self.database = self
        self.deleted = []
        self.roles = []

    def delete_agent(self, agent_id, actor, confirmed=False):
        self.deleted.append((agent_id, actor, confirmed))

    def replace_agent_roles(self, agent_id, roles, actor, reason):
        self.roles.append((agent_id, roles, actor, reason))


def make_service():
    supervisor = FakeSupervisor()
    management = FakeManagement()
    settings = {"theme": "dark", "interface_language": "ru", "message_sounds_enabled": True}
    service = SupervisorChatApplicationService(
        supervisor_service=supervisor,
        universal_service=FakeUniversal(),
        management_service=management,
        settings=settings,
        save_settings=lambda value: None,
        local_runtime=SimpleNamespace(decide=lambda _text: "SOCIAL"),
    )
    return service, management, settings


def test_lightweight_request_uses_local_route():
    service, _management, _settings = make_service()
    result = service.handle("покажи статус")
    assert result.ok
    assert result.route == "LOCAL"
    assert result.action == "list_goals"


def test_dangerous_request_requires_confirmation_then_executes():
    service, management, _settings = make_service()
    pending = service.handle("удали сотрудника agent-old")
    assert pending.confirmation_required
    result = service.confirm(pending.confirmation_token)
    assert result.ok
    assert management.deleted == [("agent-old", "ORGANIZATION_OWNER", True)]


def test_supervisor_changes_language_through_settings_callback():
    saved = []
    service, _management, settings = make_service()
    service.save_settings = lambda value: saved.append(dict(value))
    result = service.handle("смени язык на украинский")
    assert result.ok
    assert settings["interface_language"] == "uk"
    assert saved[-1]["interface_language"] == "uk"


def test_team_creation_uses_application_service():
    service, _management, _settings = make_service()
    result = service.handle("создай команду: PCB")
    assert result.ok
    assert result.action == "create_team"
    assert result.data["employee_ids"] == ["agent-one"]
