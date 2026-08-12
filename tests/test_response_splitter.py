from core.response_splitter import ResponseSplitter


def test_splits_inline_speaker_labels():
    aliases = {"Анна": "anna", "Максим": "maxim"}
    parts = ResponseSplitter.split("Анна: Начну. Максим: Подхвачу. Анна: Закрою.", "anna", aliases)

    assert [(part.role, part.content) for part in parts] == [
        ("anna", "Начну."),
        ("maxim", "Подхвачу."),
        ("anna", "Закрою."),
    ]


def test_keeps_plain_response_on_default_role():
    parts = ResponseSplitter.split("Просто отвечаю без сценки.", "petr")

    assert len(parts) == 1
    assert parts[0].role == "petr"
    assert parts[0].content == "Просто отвечаю без сценки."


def test_keeps_prefix_before_first_label():
    parts = ResponseSplitter.split("Сначала мысль. Максим: Потом реплика.", "anna", {"Максим": "maxim"})

    assert [(part.role, part.content) for part in parts] == [
        ("anna", "Сначала мысль."),
        ("maxim", "Потом реплика."),
    ]
