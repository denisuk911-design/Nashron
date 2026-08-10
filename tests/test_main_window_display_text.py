from core.structured_response import parse_agent_response
from gui.main_window import MainWindow


def test_structured_only_response_displays_summary_instead_of_json():
    parsed = parse_agent_response(
        '{"schema_version":"1.0","agent_id":"agent-shushan","role":"DOCUMENT_CONTROL_OFFICER",'
        '"task_id":"TASK-1","run_id":"RUN-1","action":"MESSAGE",'
        '"summary":"Updated document standard notes.",'
        '"files_read":[],"files_created":[],"files_modified":[],"files_deleted":[],'
        '"checks":[],"findings":[],"risks":[]}'
    )

    assert MainWindow._display_text_from_parsed_response(parsed) == "Updated document standard notes."


def test_raw_structured_response_displays_summary_instead_of_json():
    content = (
        '{"schema_version":"1.0","agent_id":"agent-shushan","role":"DOCUMENT_CONTROL_OFFICER",'
        '"task_id":"TASK-1","run_id":"RUN-1","action":"MESSAGE",'
        '"summary":"Updated document standard notes.",'
        '"files_read":[],"files_created":[],"files_modified":[],"files_deleted":[],'
        '"checks":[],"findings":[],"risks":[]}'
    )

    assert MainWindow._display_text_from_raw_response(content) == "Updated document standard notes."
