from core.conversation_mode import ConversationMode, infer_mode


def test_casual_message_leaves_work_mode_after_task_is_finished():
    assert infer_mode("Куку", ConversationMode.WORK) == ConversationMode.SOCIAL
    assert infer_mode("Привет, как дела?", ConversationMode.WORK) == ConversationMode.SOCIAL


def test_explicit_work_request_enters_work_mode():
    assert infer_mode("Проверь файл BOM", ConversationMode.SOCIAL) == ConversationMode.WORK
