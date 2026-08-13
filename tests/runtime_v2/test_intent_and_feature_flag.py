from runtime_v2.feature_flag import RuntimeEngine, selected_runtime
from runtime_v2.intent_gate import WorkIntentGate
from runtime_v2.models import WorkIntent


def test_golden_social_messages_never_create_work_intent():
    gate = WorkIntentGate()
    assert gate.classify("Привет") == WorkIntent.SOCIAL
    assert gate.classify("Как дела?") == WorkIntent.SOCIAL
    assert gate.classify("Расскажи анекдот") == WorkIntent.SOCIAL


def test_work_lifecycle_intents_depend_on_active_workflow():
    gate = WorkIntentGate()
    assert gate.classify("Создайте итоговый документ") == WorkIntent.WORK_REQUEST
    assert gate.classify("Продолжайте", active_workflow=True) == WorkIntent.WORK_CONTINUATION
    assert gate.classify("Стоп, измените требование", active_workflow=True) == WorkIntent.WORK_STOP
    assert gate.classify("Исправьте формат", active_workflow=True) == WorkIntent.WORK_MODIFICATION
    assert gate.classify("Проверьте результат", active_workflow=True) == WorkIntent.WORK_REVIEW


def test_runtime_v2_is_available_only_in_developer_mode():
    assert selected_runtime({"runtime_engine": "V2_EXPERIMENTAL"}) == RuntimeEngine.LEGACY
    assert selected_runtime({"developer_mode": True, "runtime_engine": "V2_EXPERIMENTAL"}) == RuntimeEngine.V2_EXPERIMENTAL
    assert selected_runtime({"developer_mode": True, "runtime_engine": "unknown"}) == RuntimeEngine.LEGACY
