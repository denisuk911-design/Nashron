from gui.localization import permission_label, readiness_label, role_label, tr


def test_russian_localization_uses_user_facing_labels():
    assert tr("ru", "add_employee") == "Добавить сотрудника"
    assert role_label("ru", "QA_ENGINEER") == "Инженер ОТК"
    assert permission_label("ru", "READ_WORKSPACE") == "Читать рабочую папку"
    assert readiness_label("ru", "AUTHENTICATION_REQUIRED") == "Нужна авторизация"


def test_ukrainian_and_english_localization_are_available():
    assert tr("uk", "add_employee") == "Додати співробітника"
    assert role_label("uk", "CUSTOM_ROLE") == "Інша роль"
    assert tr("en", "add_employee") == "Add employee"
