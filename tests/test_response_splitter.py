from core.response_splitter import ResponseSplitter


def test_splits_inline_speaker_labels():
    parts = ResponseSplitter.split("Роман: Начну. Петр: Подхвачу. Роман: Закрою.", "roman")

    assert [(part.role, part.content) for part in parts] == [
        ("roman", "Начну."),
        ("petr", "Подхвачу."),
        ("roman", "Закрою."),
    ]


def test_keeps_plain_response_on_default_role():
    parts = ResponseSplitter.split("Просто отвечаю без сценки.", "petr")

    assert len(parts) == 1
    assert parts[0].role == "petr"
    assert parts[0].content == "Просто отвечаю без сценки."


def test_keeps_prefix_before_first_label():
    parts = ResponseSplitter.split("Сначала мысль. Петр: Потом реплика.", "roman")

    assert [(part.role, part.content) for part in parts] == [
        ("roman", "Сначала мысль."),
        ("petr", "Потом реплика."),
    ]
