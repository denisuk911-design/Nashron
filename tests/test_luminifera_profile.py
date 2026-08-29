from __future__ import annotations

import pytest

from ui_luminifera.profile import LuminiferaProfileDialog


def test_profile_dialog_keeps_owner_identity_editable():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    dialog = LuminiferaProfileDialog({"owner_display_name": "Василий", "user_avatar_path": ""})
    dialog.name.setText("Новый владелец")
    assert dialog.values()["owner_display_name"] == "Новый владелец"
    dialog._remove_avatar()
    assert dialog.values()["user_avatar_path"] == ""
    dialog.close()
