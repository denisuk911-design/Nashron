from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMessageBox

from core.settings_service import SettingsService
from core.unicode_pipeline import validate_unicode_catalog
from gui.main_window import MainWindow
from gui.startup_splash import StartupSplash


def setup_logging(settings_service: SettingsService) -> logging.Logger:
    paths = settings_service.ensure_user_files()
    logger = logging.getLogger("roman2050")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(
            paths.logs_dir / "roman2050.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    return logger


def main() -> int:
    settings_service = SettingsService()
    logger = setup_logging(settings_service)
    unicode_errors = validate_unicode_catalog()
    if unicode_errors:
        logger.error("unicode_catalog_invalid errors=%s", ";".join(unicode_errors))
    app = QApplication(sys.argv)
    app.setApplicationName("Team2050")
    app.setOrganizationName("Roman2050")

    lock = QLockFile(str(settings_service.paths.user_dir / "roman2050.lock"))
    lock.setStaleLockTime(30000)
    if not lock.tryLock(100):
        QMessageBox.information(None, "Team2050", "Программа уже запущена")
        return 0

    splash = StartupSplash()
    splash.show()
    app.processEvents()
    splash.set_status("Загружаю настройки и базу данных")
    app.processEvents()
    window = MainWindow(settings_service, logger)
    splash.set_status("Открываю рабочий чат")
    app.processEvents()
    window.show()
    splash.close()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
