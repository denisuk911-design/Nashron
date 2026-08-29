from __future__ import annotations

from ui_luminifera.states import product_failure_message


def test_product_failure_message_explains_safety_and_next_action():
    text = product_failure_message("ru")
    assert "Данные в безопасности" in text
    assert "Проверьте" in text
