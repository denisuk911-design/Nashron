from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from gui.chat.message_widget import MessageWidget
from gui.chat_widget import ChatWidget


def app():
    return QApplication.instance() or QApplication([])


def test_final_response_replaces_structured_stream_placeholder():
    app()
    widget = ChatWidget()
    widget.set_stream_role("agent-shushan")
    widget.append_roman_delta(
        '{"schema_version":"1.0","agent_id":"agent-shushan","role":"DOCUMENT_CONTROL_OFFICER",'
        '"task_id":"TASK-1","run_id":"RUN-1","action":"MESSAGE",'
        '"summary":"Updated document standard notes.",'
        '"files_read":[],"files_created":[],"files_modified":["docs/SKILL_GOST.md"],'
        '"files_deleted":[],"checks":[],"findings":[],"risks":[]}'
    )
    while widget._typewriter_queue:
        widget._flush_typewriter()

    widget.finish_roman_response("Updated document standard notes.")

    assert widget.messages.count() == 1
    item = widget.messages.item(0)
    message = widget.messages.itemWidget(item)
    assert isinstance(message, MessageWidget)
    assert message.content == "Updated document standard notes."
    assert item.data(Qt.UserRole)["content"] == "Updated document standard notes."


def test_final_response_replaces_json_prefixed_stream_placeholder():
    app()
    widget = ChatWidget()
    widget.set_stream_role("agent-shushan")
    widget.append_roman_delta(
        'json\n{"schema_version":"1.0","agent_id":"agent-shushan","role":"DOCUMENT_CONTROL_OFFICER",'
        '"task_id":"TASK-1","run_id":"RUN-1","action":"MESSAGE",'
        '"summary":"Updated document standard notes.",'
        '"files_read":[],"files_created":[],"files_modified":["docs/SKILL_GOST.md"],'
        '"files_deleted":[],"checks":[],"findings":[],"risks":[]}'
    )
    while widget._typewriter_queue:
        widget._flush_typewriter()

    widget.finish_roman_response("Updated document standard notes.")

    assert widget.messages.count() == 1
    item = widget.messages.item(0)
    message = widget.messages.itemWidget(item)
    assert isinstance(message, MessageWidget)
    assert message.content == "Updated document standard notes."
    assert item.data(Qt.UserRole)["content"] == "Updated document standard notes."


def test_multiline_message_height_expands_to_show_full_text():
    app()
    widget = ChatWidget()
    widget.resize(900, 600)
    text = "\n".join(
        [
            "Long engineering note with enough content to wrap across several lines in the message bubble.",
            "Second line: the card must grow instead of clipping the visible text behind the rounded bubble.",
            "Third line: streaming updates and final messages use the same size hint path.",
            "Fourth line: this catches regressions in manual height calculation.",
        ]
    )

    item = widget.add_message("roman", text)
    message = widget.messages.itemWidget(item)

    assert isinstance(message, MessageWidget)
    assert item.sizeHint().height() >= message.body.sizeHint().height() + 50
    assert item.sizeHint().height() > 120


def test_message_body_geometry_contains_all_wrapped_text():
    app()
    widget = ChatWidget()
    widget.resize(900, 600)
    item = widget.add_message(
        "roman",
        "A long PCB review message with enough words to wrap several times. " * 12,
    )
    widget._resize_message_widgets()
    QApplication.processEvents()
    message = widget.messages.itemWidget(item)

    assert isinstance(message, MessageWidget)
    assert message.body.geometry().bottom() <= message.card.contentsRect().bottom()
    assert item.sizeHint().height() >= message.sizeHint().height() + 30


def test_goal_mode_and_banner_are_visible():
    app()
    widget = ChatWidget()
    index = widget.mode_selector.findData("goal")
    widget.mode_selector.setCurrentIndex(index)

    assert widget.routing_options()["goal_mode"] is True
    assert widget.goal_mode_requested()

    widget.set_goal_status(True, "создать документ", 2)
    assert not widget.goal_banner.isHidden()
    assert "создать документ" in widget.goal_banner.text()
    assert "2" in widget.goal_banner.text()

    widget.set_goal_status(False)
    assert widget.goal_banner.isHidden()
