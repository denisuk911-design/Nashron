from PySide6.QtWidgets import QApplication, QTabWidget

from gui.settings_dialog import SettingsDialog


def test_settings_controls_are_distributed_between_real_tabs() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog({"interface_language": "ru"})
    tabs = dialog.findChild(QTabWidget)
    assert tabs is not None
    assert tabs.count() == 7
    assert dialog.theme.parentWidget() is tabs.widget(1)
    assert dialog.message_sounds.parentWidget() is tabs.widget(2)
    assert dialog.allow_local_tools.parentWidget() is tabs.widget(3)
    assert tabs.widget(5).isAncestorOf(dialog.workspace)
    app.processEvents()
