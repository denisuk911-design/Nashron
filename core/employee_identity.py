from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random


@dataclass(frozen=True)
class GeneratedIdentity:
    name: str
    gender: str
    biography: str
    avatar_path: str | None


_NAMES = {
    "ru": {
        "ukrainian": {
            "female": [("Олена", "Коваль"), ("София", "Мельник"), ("Ирина", "Бондаренко"), ("Марина", "Шевченко")],
            "male": [("Андрей", "Кравченко"), ("Тарас", "Бойко"), ("Никита", "Ткаченко"), ("Олег", "Романюк")],
        },
        "other": {
            "female": [("Анна", "Волкова"), ("Мария", "Орлова"), ("Ева", "Морозова"), ("Лаура", "Соколова")],
            "male": [("Максим", "Лебедев"), ("Даниил", "Козлов"), ("Алексей", "Федоров"), ("Марк", "Смирнов")],
        },
    },
    "uk": {
        "ukrainian": {
            "female": [("Олена", "Коваль"), ("Софія", "Мельник"), ("Ірина", "Бондаренко"), ("Марина", "Шевченко")],
            "male": [("Андрій", "Кравченко"), ("Тарас", "Бойко"), ("Микита", "Ткаченко"), ("Олег", "Романюк")],
        },
        "other": {
            "female": [("Анна", "Волкова"), ("Марія", "Орлова"), ("Єва", "Морозова"), ("Лаура", "Соколова")],
            "male": [("Максим", "Лебедєв"), ("Данило", "Козлов"), ("Олексій", "Федоров"), ("Марк", "Смирнов")],
        },
    },
    "en": {
        "ukrainian": {
            "female": [("Olena", "Koval"), ("Sofia", "Melnyk"), ("Iryna", "Bondarenko"), ("Maryna", "Shevchenko")],
            "male": [("Andrii", "Kravchenko"), ("Taras", "Boiko"), ("Mykyta", "Tkachenko"), ("Oleh", "Romaniuk")],
        },
        "other": {
            "female": [("Anna", "Volkova"), ("Maria", "Orlova"), ("Eva", "Morozova"), ("Laura", "Sokolova")],
            "male": [("Maxim", "Lebedev"), ("Daniel", "Kozlov"), ("Alex", "Fedorov"), ("Mark", "Smirnov")],
        },
    },
}

_BIOGRAPHIES = {
    "ru": {
        "female": ["Инженер по документации, любит порядок в требованиях и понятные результаты.", "Проектировщица электронных систем, проверяет факты и спокойно разбирает сложные задачи."],
        "male": ["Инженер по качеству, ищет ошибки до выпуска результата и фиксирует проверяемые выводы.", "Разработчик PCB, предпочитает короткий план, измеримые проверки и аккуратную документацию."],
    },
    "uk": {
        "female": ["Інженерка з документації, любить порядок у вимогах і зрозумілі результати.", "Проєктувальниця електронних систем, перевіряє факти й спокійно розбирає складні задачі."],
        "male": ["Інженер з якості, знаходить помилки до випуску результату й фіксує перевірювані висновки.", "Розробник PCB, віддає перевагу короткому плану, вимірюваним перевіркам і точній документації."],
    },
    "en": {
        "female": ["Documentation engineer who values clear requirements and verifiable results.", "Electronics designer who checks facts and breaks complex tasks into practical steps."],
        "male": ["Quality engineer who finds defects before release and records verifiable conclusions.", "PCB designer who prefers short plans, measurable checks and precise documentation."],
    },
}


def generate_identity(language: str = "ru", gender: str = "random", avatar_dir: Path | None = None) -> GeneratedIdentity:
    language = language if language in _NAMES else "ru"
    selected_gender = gender if gender in {"female", "male"} else random.choice(("female", "male"))
    family = "ukrainian" if random.random() < 0.5 else "other"
    first_name, last_name = random.choice(_NAMES[language][family][selected_gender])
    biography = random.choice(_BIOGRAPHIES[language][selected_gender])
    avatar_path = _pick_avatar(avatar_dir, selected_gender)
    return GeneratedIdentity(f"{first_name} {last_name}", selected_gender, biography, avatar_path)


def _pick_avatar(avatar_dir: Path | None, gender: str) -> str | None:
    if avatar_dir is None or not avatar_dir.exists():
        return None
    gender_token = "woman" if gender == "female" else "man"
    matching = [path for path in avatar_dir.glob("avatar-*.png") if gender_token in path.stem or "cat-" in path.stem or "dog-" in path.stem or "reaction-" in path.stem]
    if not matching:
        matching = list(avatar_dir.glob("*.png"))
    return str(random.choice(matching)) if matching else None
