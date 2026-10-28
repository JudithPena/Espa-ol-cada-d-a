import json

from espanol import __main__ as cli
from espanol.botdata import bot_words, export, word_id
from espanol.telegram import TelegramError


def test_bot_words_cover_course_once_in_order(course):
    words = bot_words(course)
    assert len({w.key for w in words}) == len(words)
    order = [w.lesson.index for w in words]
    assert order == sorted(order)


def test_export_without_audio(tmp_path, course):
    result = export(course, tmp_path, audio=False)
    records = json.loads((tmp_path / "data" / "words.json").read_text(encoding="utf-8"))
    assert result == {"words": len(records), "audio": 0, "deck": 0, "videos": 0}
    assert json.loads((tmp_path / "data" / "videos.json").read_text(encoding="utf-8")) == []
    lesson_ids = {lesson.id for lesson in course.lessons}
    for r in records:
        assert r["lesson"] in lesson_ids and r["es"] and r["ru"] and not r["audio"]
        assert "**" not in r["ru"] and "_" not in r["es"]  # без разметки курса
    hola = next(r for r in records if r["es"] == "¡Hola!")
    assert hola["id"] == word_id(next(w for w in bot_words(course) if w.es == "¡Hola!"))


def test_send_auto_uses_review_chat_when_bot_has_webhook(monkeypatch, capsys):
    """Когда бот работает на Cloudflare, getUpdates недоступен: тест в личку идёт в TELEGRAM_REVIEW_CHAT_ID."""
    sent = []

    class FakePublisher:
        class api:
            @staticmethod
            def latest_private_chat():
                raise TelegramError("getUpdates: 409 Conflict: can't use getUpdates method while webhook is active")

        def render(self, lesson, rich=False):
            return []

        def send(self, messages, chat, lesson=None):
            sent.append(chat)

    monkeypatch.setattr(cli, "make_publisher", lambda *a: FakePublisher())
    monkeypatch.delenv("TELEGRAM_REVIEW_CHAT_ID", raising=False)
    assert cli.main(["send", "0", "--chat", "auto"]) == 1
    assert "TELEGRAM_REVIEW_CHAT_ID" in capsys.readouterr().out
    monkeypatch.setenv("TELEGRAM_REVIEW_CHAT_ID", "12345")
    assert cli.main(["send", "0", "--chat", "auto"]) == 0
    assert sent == ["12345"]


def test_audio_has_word_as_title(tmp_path, course, monkeypatch):
    """Telegram подписывает аудио по тегу ID3 — там слово, а не имя файла."""
    from espanol import botdata, tts

    monkeypatch.setattr(tts, "available", lambda: True)
    monkeypatch.setattr(tts, "synthesize", lambda segments, rate, **kw: b"\xff\xfbMP3")
    monkeypatch.setattr(botdata, "bot_words", lambda c: bot_words(c)[:2])
    export(course, tmp_path, cache=tmp_path / "cache")
    record = json.loads((tmp_path / "data" / "words.json").read_text(encoding="utf-8"))[0]
    data = (tmp_path / "public" / "audio" / record["audio"]).read_bytes()
    assert data.startswith(b"ID3\x03") and data.endswith(b"\xff\xfbMP3")
    assert record["es"].encode("utf-16-le") in data and "Español cada día".encode("utf-16-le") in data


def test_lessons_end_with_repaso_link(course, renderer):
    """В конце урока — ссылка на бота: слова этого урока, а без новых слов — обычное повторение."""
    with_words = next(lesson for lesson in course.lessons if any(i.srs for i in lesson.vocab))
    link = renderer.repaso_link(with_words)
    assert f"t.me/{course.bot}?start=l-{with_words.id.replace('/', '-')}" in link
    no_words = next(lesson for lesson in course.lessons if not lesson.vocab)
    assert "?start=repaso" in renderer.repaso_link(no_words)
    html = "".join(getattr(m, "html", "") for m in renderer.render(with_words))
    assert link in html
