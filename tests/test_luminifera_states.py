from __future__ import annotations

from ui_luminifera.states import product_failure_message, product_state


def test_product_state_catalog_has_safe_actionable_copy_for_all_languages():
    for language in ("ru", "uk", "en"):
        state = product_state(language, "provider_unavailable")
        assert state["title"]
        assert state["body"]
        assert state["action"]
        assert "provider_error" not in state["body"]


def test_product_failure_message_explains_safety_and_next_action():
    text = product_failure_message("ru")
    assert "Данные в безопасности" in text
    assert "Проверьте" in text
