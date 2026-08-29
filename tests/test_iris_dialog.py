from __future__ import annotations

import pytest

from gui.supervisor_chat_dialog import SupervisorChatDialog


class _Service:
    def handle(self, *_args, **_kwargs):
        raise AssertionError("not part of this view test")

    def confirm(self, *_args, **_kwargs):
        raise AssertionError("not part of this view test")


def test_iris_dialog_is_the_only_visible_owner_name():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    dialog = SupervisorChatDialog(_Service(), None)
    assert dialog.windowTitle() == "Iris - Luminifera"
    assert "Iris" in dialog.editor.placeholderText()
    assert "Luminifera" in dialog.findChild(widgets.QLabel, "irisChatIntro").text()
    assert all("Supervisor" not in label.text() for label in dialog.findChildren(widgets.QLabel))
    dialog.close()
