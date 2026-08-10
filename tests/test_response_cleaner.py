from core.response_cleaner import ResponseCleaner


def test_removes_repeated_paragraphs():
    text = "Первый абзац.\n\nПовтор.\n\nПовтор.\n\nФинал."
    assert ResponseCleaner.clean(text) == "Первый абзац. Повтор. Финал."


def test_removes_repeated_sentences():
    text = "Сделаю. Сделаю. Потом проверю."
    assert ResponseCleaner.clean(text) == "Сделаю. Потом проверю."
