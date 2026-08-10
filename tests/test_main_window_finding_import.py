from core.structured_response import ParsedAgentResponse
from gui.main_window import MainWindow


def test_invalid_structured_response_does_not_import_findings():
    class FakeFindingService:
        def __init__(self):
            self.calls = 0

        def import_from_structured_response(self, **_kwargs):
            self.calls += 1
            return ["FIND-1"]

    class FakeDatabase:
        def log_event(self, *_args):
            pass

    window = MainWindow.__new__(MainWindow)
    window.finding_service = FakeFindingService()
    window.database = FakeDatabase()
    parsed = ParsedAgentResponse(
        human_text="Review text",
        envelope={"findings": [{"description": "Issue"}]},
        errors=["missing_fields:schema_version"],
    )

    created = MainWindow._import_structured_findings(window, None, parsed, "petr")

    assert created == []
    assert window.finding_service.calls == 0
