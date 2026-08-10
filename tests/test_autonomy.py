from core.autonomy import detect_peer_handoff, is_stop_command, parse_autonomy_request


def test_detects_free_discussion_request():
    request = parse_autonomy_request("говорити между собой о плане")

    assert request.enabled
    assert not request.complete_on_goal
    assert "плане" in request.goal


def test_detects_goal_request():
    request = parse_autonomy_request("цель: придумать план и остановиться")

    assert request.enabled
    assert request.complete_on_goal
    assert request.goal == "придумать план и остановиться"


def test_detects_stop_command():
    assert is_stop_command("  стоп  ")
    assert is_stop_command("хватит")
    assert not is_stop_command("стопнись когда закончишь")


def test_work_task_does_not_become_autonomous_without_magic_phrase():
    request = parse_autonomy_request("Создай локальный скилл и обучайся на нём")

    assert not request.enabled
    assert not request.complete_on_goal


def test_work_task_becomes_goal_with_explicit_until_done_phrase():
    request = parse_autonomy_request("Работайте пока не выполните: создайте локальный скилл")

    assert request.enabled
    assert request.complete_on_goal


def test_detects_peer_handoff_from_roman_to_petr():
    text = "Петр, дам тебе структуру на просмотр. Проверь без воды."

    assert detect_peer_handoff(text, "roman") == "petr"


def test_peer_mention_without_action_does_not_handoff():
    text = "Петр уже отвечал выше, я не буду повторять его позицию."

    assert detect_peer_handoff(text, "roman") is None
