from core.runtime_v3_service import RuntimeV3GoalService


def test_explicit_work_intent_does_not_confuse_social_chat_with_goal():
    assert not RuntimeV3GoalService.is_explicit_work_intent("привет, как дела?")
    assert RuntimeV3GoalService.is_explicit_work_intent("сделай проверяемый файл")
    assert RuntimeV3GoalService.is_explicit_work_intent("проверь документацию")
