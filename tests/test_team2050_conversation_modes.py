from test_prompt_builder import make_builder


def test_social_mode_keeps_work_context_in_background(tmp_path):
    builder, database = make_builder(tmp_path)
    conversation_id = database.create_conversation()

    prompt = builder.build(
        conversation_id,
        "Расскажи короткий анекдот",
        task_id="TASK-1",
        conversation_mode="SOCIAL",
        active_work_context_lines=["- task title: Build converter"],
    )

    assert "conversation_mode: SOCIAL" in prompt
    assert "Не возвращай разговор к работе без прямого рабочего запроса пользователя." in prompt
    assert "current_task_id: нет" in prompt
    assert "task title: Build converter" not in prompt
