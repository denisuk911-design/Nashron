from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import random

from core.avatar_catalog import list_avatar_files


@dataclass(frozen=True)
class GeneratedIdentity:
    name: str
    gender: str
    biography: str
    avatar_path: str | None
    preferred_name: str = ""
    informal_name: str = ""
    communication_profile: dict[str, object] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return self.name


_FIRST_NAMES = {
    "ru": {
        "ukrainian": {
            "female": ["Олена", "София", "Ирина", "Марина", "Анна", "Дарья", "Наталья", "Екатерина", "Виктория", "Юлия", "Лилия", "Зоряна"],
            "male": ["Андрей", "Тарас", "Никита", "Олег", "Богдан", "Дмитрий", "Максим", "Артём", "Владислав", "Роман", "Ярослав", "Игорь"],
        },
        "other": {
            "female": ["Алина", "Мария", "Ева", "Лаура", "Сара", "Диана", "Эмма", "Майя", "Наоми", "Адель", "Нора", "Лейла"],
            "male": ["Алекс", "Даниэль", "Марк", "Леон", "Томас", "Самир", "Мартин", "Оскар", "Давид", "Эрик", "Роберт", "Амир"],
        },
    },
    "uk": {
        "ukrainian": {
            "female": ["Олена", "Софія", "Ірина", "Марина", "Ганна", "Дарина", "Наталія", "Катерина", "Вікторія", "Юлія", "Лілія", "Зоряна"],
            "male": ["Андрій", "Тарас", "Микита", "Олег", "Богдан", "Дмитро", "Максим", "Артем", "Владислав", "Роман", "Ярослав", "Ігор"],
        },
        "other": {
            "female": ["Аліна", "Марія", "Єва", "Лаура", "Сара", "Діана", "Емма", "Мая", "Наомі", "Адель", "Нора", "Лейла"],
            "male": ["Алекс", "Даніель", "Марк", "Леон", "Томас", "Самір", "Мартін", "Оскар", "Давид", "Ерік", "Роберт", "Амір"],
        },
    },
    "en": {
        "ukrainian": {
            "female": ["Olena", "Sofiia", "Iryna", "Maryna", "Anna", "Daryna", "Nataliia", "Kateryna", "Viktoriia", "Yuliia", "Liliia", "Zoriana"],
            "male": ["Andrii", "Taras", "Mykyta", "Oleh", "Bohdan", "Dmytro", "Maksym", "Artem", "Vladyslav", "Roman", "Yaroslav", "Ihor"],
        },
        "other": {
            "female": ["Alina", "Maria", "Eva", "Laura", "Sarah", "Diana", "Emma", "Maya", "Naomi", "Adele", "Nora", "Leila"],
            "male": ["Alex", "Daniel", "Mark", "Leon", "Thomas", "Samir", "Martin", "Oscar", "David", "Eric", "Robert", "Amir"],
        },
    },
}

_SURNAMES = {
    "ru": {
        "ukrainian": ["Коваль", "Мельник", "Бондаренко", "Шевченко", "Кравченко", "Бойко", "Ткаченко", "Романюк", "Козак", "Полищук", "Савченко", "Марченко", "Левченко", "Остапенко", "Гриценко", "Петренко"],
        "other": ["Новак", "Вебер", "Мартин", "Росси", "Ким", "Ли", "Сильва", "Мюллер", "Гарсия", "Смит", "Коэн", "Хаддад", "Йоханссон", "Беннет", "Патель", "Танака"],
    },
    "uk": {
        "ukrainian": ["Коваль", "Мельник", "Бондаренко", "Шевченко", "Кравченко", "Бойко", "Ткаченко", "Романюк", "Козак", "Поліщук", "Савченко", "Марченко", "Левченко", "Остапенко", "Гриценко", "Петренко"],
        "other": ["Новак", "Вебер", "Мартін", "Россі", "Кім", "Лі", "Сілва", "Мюллер", "Гарсія", "Сміт", "Коен", "Хаддад", "Йоганссон", "Беннет", "Патель", "Танака"],
    },
    "en": {
        "ukrainian": ["Koval", "Melnyk", "Bondarenko", "Shevchenko", "Kravchenko", "Boiko", "Tkachenko", "Romaniuk", "Kozak", "Polishchuk", "Savchenko", "Marchenko", "Levchenko", "Ostapenko", "Hrytsenko", "Petrenko"],
        "other": ["Novak", "Weber", "Martin", "Rossi", "Kim", "Lee", "Silva", "Mueller", "Garcia", "Smith", "Cohen", "Haddad", "Johansson", "Bennett", "Patel", "Tanaka"],
    },
}

_BIOGRAPHY_PARTS = {
    "ru": {
        "origins": ["Вырос в небольшом городе и привык рассчитывать на факты", "Любит разбираться в сложных системах и объяснять их простыми словами", "Ценит спокойную работу, ясные договорённости и хороший юмор", "Предпочитает сначала понять задачу, а затем действовать"],
        "interests": ["В свободное время фотографирует город", "По выходным ходит в походы", "Собирает настольные игры", "Любит джаз и старое кино", "Готовит для друзей", "Читает научно-популярные книги"],
        "work": ["В команде говорит прямо, но уважительно.", "Не любит пустые отчёты и фиксирует только проверяемый результат.", "Спокойно спорит по существу и умеет менять мнение после сильных аргументов.", "Предпочитает короткие сообщения и заранее предупреждает о рисках."],
    },
    "uk": {
        "origins": ["Виріс у невеликому місті та звик покладатися на факти", "Любить розбиратися у складних системах і пояснювати їх простими словами", "Цінує спокійну роботу, чіткі домовленості та добрий гумор", "Вважає за краще спочатку зрозуміти завдання, а потім діяти"],
        "interests": ["У вільний час фотографує місто", "На вихідних ходить у походи", "Збирає настільні ігри", "Любить джаз і старе кіно", "Готує для друзів", "Читає науково-популярні книжки"],
        "work": ["У команді говорить прямо, але з повагою.", "Не любить порожні звіти й фіксує лише перевірений результат.", "Спокійно сперечається по суті та змінює думку після сильних аргументів.", "Віддає перевагу коротким повідомленням і завчасно попереджає про ризики."],
    },
    "en": {
        "origins": ["Grew up in a small city and learned to rely on evidence", "Enjoys understanding complex systems and explaining them plainly", "Values calm work, clear agreements and good humor", "Prefers to understand a problem before taking action"],
        "interests": ["Photographs city life after work", "Goes hiking on weekends", "Collects board games", "Enjoys jazz and classic films", "Cooks for friends", "Reads popular science"],
        "work": ["Speaks directly but respectfully with the team.", "Dislikes empty reporting and records only verifiable results.", "Disagrees calmly and changes course when the evidence is stronger.", "Prefers concise messages and flags risks early."],
    },
}

_INFORMAL_SUFFIXES = {
    "ru": {"female": ["", "ка", "ша"], "male": ["", "ыч", "ян"]},
    "uk": {"female": ["", "ка"], "male": ["", "ко"]},
    "en": {"female": ["", "y"], "male": ["", "y"]},
}


def generate_identity(language: str = "ru", gender: str = "random", avatar_dir: Path | None = None) -> GeneratedIdentity:
    language = language if language in _FIRST_NAMES else "ru"
    selected_gender = gender if gender in {"female", "male"} else random.choice(("female", "male"))
    family = "ukrainian" if random.random() < 0.5 else "other"
    first_name = random.choice(_FIRST_NAMES[language][family][selected_gender])
    last_name = random.choice(_SURNAMES[language][family])
    biography = " ".join(random.choice(_BIOGRAPHY_PARTS[language][part]) for part in ("origins", "interests", "work"))
    informal_name = _informal_name(first_name, language, selected_gender)
    return GeneratedIdentity(
        name=f"{first_name} {last_name}",
        gender=selected_gender,
        biography=biography,
        avatar_path=_pick_avatar(avatar_dir, selected_gender),
        preferred_name=first_name,
        informal_name=informal_name,
        communication_profile=_generate_communication_profile(),
    )


def _generate_communication_profile() -> dict[str, object]:
    return {
        "directness": random.randint(2, 5),
        "warmth": random.randint(2, 5),
        "formality": random.randint(1, 4),
        "humor": random.randint(0, 3),
        "assertiveness": random.randint(2, 5),
        "verbosity": random.randint(1, 3),
        "initiative": random.randint(2, 5),
        "emotionality": random.randint(1, 5),
        "explanation_style": random.choice(("short", "detailed", "examples", "technical")),
        "disagreement_style": random.choice(("evidence_first", "diplomatic", "direct")),
    }


def _informal_name(first_name: str, language: str, gender: str) -> str:
    if language == "en":
        return first_name if len(first_name) <= 5 else first_name[:4]
    suffix = random.choice(_INFORMAL_SUFFIXES[language][gender])
    if not suffix or len(first_name) < 5:
        return first_name
    return f"{first_name[:4]}{suffix}"


def _pick_avatar(avatar_dir: Path | None, gender: str) -> str | None:
    available = list_avatar_files(avatar_dir)
    if not available:
        return None
    gender_token = "woman" if gender == "female" else "man"
    matching = [path for path in available if gender_token in path.stem.lower()]
    # Every valid catalog item remains eligible; matching portraits only receive
    # a preference so a generated identity usually has a plausible photo.
    # Prefer a matching portrait while still sampling the full catalog of
    # portraits, illustrations, animals and meme-style avatars broadly.
    pool = matching if matching and random.random() < 0.55 else available
    return str(random.choice(pool))
