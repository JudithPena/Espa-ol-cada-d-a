import json
from pathlib import Path

import pytest

from espanol import __main__ as cli
from espanol.botdata import export
from espanol.course import ContentError
from espanol.markup import check_html, strip_tags
from espanol.mywords import FOLDER, deck_problems, find_word, load_deck, render_card

SAMPLE = Path(__file__).resolve().parent / "data"


def test_sample_cards_are_valid():
    words = load_deck(SAMPLE)
    assert [w.word for w in words] == ["echar de menos", "subtle"]
    assert [w.lang for w in words] == ["es", "en"]
    assert deck_problems(words) == []


def test_card_has_all_sections_and_hides_details():
    card = render_card(find_word(load_deck(SAMPLE), "echar de menos"))
    assert not check_html(card)
    text = strip_tags(card)
    for part in ("🗣 /eˈtʃaɾ ðe ˈmenos/ · эча́р де ме́нос", "Значение", "Происхождение", "Регистр",
                 "Синоним: extrañar", "По-английски", "Мини-диалог", "Уровень A2", "Частотность",
                 "Сочетания", "Ловушка"):
        assert part in text
    # главное видно сразу, подробности — в раскрывающихся блоках
    assert card.index("Значение") < card.index("<blockquote expandable>") < card.index("Происхождение")
    assert "<b>Ana:</b>" in card


def test_english_word_gets_spanish_analog_and_plain_pronunciation_note():
    subtle = find_word(load_deck(SAMPLE), "subtle")
    text = strip_tags(render_card(subtle))
    assert "🇪🇸 По-испански" in text and "sutil" in text


def test_problems_are_reported(tmp_path):
    (tmp_path / FOLDER).mkdir()
    (tmp_path / FOLDER / "01_x.yaml").write_text(
        "words:\n"
        "  - {word: hola, ru: привет, ipa: /ˈola/, meaning: Привет., examples: ['Hola. — Привет.'], cefr: X1}\n"
        "  - {word: hola, ru: привет, ipa: /ˈola/}\n", encoding="utf-8")
    problems = "\n".join(deck_problems(load_deck(tmp_path)))
    assert "нет раздела trap" in problems
    assert "примеров 1, нужно 2–4" in problems
    assert "cefr начинается с уровня" in problems
    assert "такое слово уже есть" in problems


def test_broken_file_is_an_error(tmp_path):
    (tmp_path / FOLDER).mkdir()
    (tmp_path / FOLDER / "01_x.yaml").write_text("- hola\n", encoding="utf-8")
    with pytest.raises(ContentError):
        load_deck(tmp_path)


def test_export_writes_deck_for_bot(tmp_path, course):
    result = export(course, tmp_path, audio=False, deck=load_deck(SAMPLE))
    assert result["deck"] == 2
    records = json.loads((tmp_path / "data" / "mywords.json").read_text(encoding="utf-8"))
    first = records[0]
    assert first["word"] == "echar de menos" and first["ru"] == "скучать (по кому-то, чему-то)"
    assert first["ex"] == ["Echo de menos a mi familia.", "Я скучаю по своей семье."]
    assert "<blockquote expandable>" in first["card"]
    assert len(f"py:{first['id']}:c".encode()) <= 64  # callback_data в Telegram


def test_palabras_command_shows_card(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: type("S", (), {"content_dir": SAMPLE})())
    assert cli.main(["palabras"]) == 0
    assert "В колоде «Мои слова»: 2" in capsys.readouterr().out
    assert cli.main(["palabras", "subtle"]) == 0
    assert "Буква b не читается" in capsys.readouterr().out


def test_deck_audio_uses_voice_of_word_language(tmp_path, course, monkeypatch):
    from espanol import botdata, tts

    spoken = []

    def synthesize(segments, rate, voices):
        spoken.append((segments, voices[segments[0][0]]))
        return b"\xff\xfbMP3"

    monkeypatch.setattr(tts, "available", lambda: True)
    monkeypatch.setattr(tts, "synthesize", synthesize)
    monkeypatch.setattr(botdata, "bot_words", lambda c: [])
    result = export(course, tmp_path, cache=tmp_path / "cache", deck=load_deck(SAMPLE))
    assert result["audio"] == 2
    voices = {segments[0][1]: voice for segments, voice in spoken}
    assert voices == {"echar de menos": "es-ES-ElviraNeural", "subtle": "en-US-AriaNeural"}
    records = json.loads((tmp_path / "data" / "mywords.json").read_text(encoding="utf-8"))
    assert all((tmp_path / "public" / "audio" / r["audio"]).exists() for r in records)
