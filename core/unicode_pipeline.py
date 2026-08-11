from __future__ import annotations

from gui.localization import TEXT


REQUIRED_UI_LABELS = {
    "ru": ("Организация", "Сотрудники", "Профессии", "Навыки", "Обучение", "Шаблоны", "Настройки"),
    "uk": ("Організація", "Працівники", "Професії", "Навички", "Навчання", "Шаблони", "Налаштування"),
    "en": ("Organization", "Employees", "Professions", "Skills", "Learning", "Templates", "Settings"),
}


def validate_unicode_catalog() -> tuple[str, ...]:
    """Validate the UI strings that must survive source, Qt and PyInstaller."""
    errors: list[str] = []
    for language, values in REQUIRED_UI_LABELS.items():
        catalog = TEXT.get(language, {})
        for value in values:
            if value not in catalog.values():
                errors.append(f"{language}:{value}:missing")
            if "�" in value or "Р" in value and value.startswith("Р"):
                errors.append(f"{language}:{value}:mojibake")
    return tuple(errors)
