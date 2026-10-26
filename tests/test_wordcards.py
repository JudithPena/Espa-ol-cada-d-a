import json

from espanol import __main__ as cli
from espanol.botdata import bot_words, export
from espanol.markup import check_html, strip_tags
from espanol.wordcards import FOLDER, card_problems, load_cards, render_card


def write(tmp_path, text):
    (tmp_path / FOLDER).mkdir(exist_ok=True)
    (tmp_path / FOLDER / "01_x.yaml").write_text(text, encoding="utf-8")
    return load_cards(tmp_path)


def test_card_without_analysis_is_built_from_lesson(course):
    item = next(i for i in bot_words(course) if i.example)
    html = render_card(item)
    assert not check_html(html)
    assert item.ru in strip_tags(html) and item.example.ru in strip_tags(html)


def test_short_card_and_checks(tmp_path, course, lexicon):
    cards = write(tmp_path, """
words:
  - es: la casa
    pron: "c перед a — как русское «к»."
    meaning: "Дом, где живут."
    examples: ["Hola, casa. — Привет, дом."]
    collocations: ["en casa — дома"]
    trap: "Не путайте с caza — «охота»."
  - es: el taxi
    meaning: "Такси."
    examples: ["Un taxi grande. — Большое такси."]
  - es: no-такого-слова
    meaning: "…"
    examples: ["No. — Нет."]
""")
    casa = next(i for i in bot_words(course) if i.key == "la casa")
    text = strip_tags(render_card(casa, cards["la casa"]))
    for part in ("la casa", "Значение", "Hola, casa.", "Сочетания", "Ловушка"):
        assert part in text
    problems = "\n".join(card_problems(course, lexicon, cards))
    assert "la casa" not in problems
    assert "не пройдены к уроку" in problems and "grande" in problems  # grande — слово позже
    assert "такого слова нет в уроках" in problems


def test_export_puts_cards_into_words_json(tmp_path, course):
    cards = write(tmp_path, 'words:\n  - es: la casa\n    meaning: "Дом."\n    examples: ["Hola, casa. — Привет, дом."]\n')
    export(course, tmp_path, audio=False, cards=cards)
    records = {r["word"]: r for r in json.loads((tmp_path / "data" / "words.json").read_text(encoding="utf-8"))}
    assert "Значение" in records["la casa"]["card"]
    assert records["el taxi"]["card"].startswith("🚕 <b>el taxi</b>") or "el taxi" in records["el taxi"]["card"]
    assert records["la casa"]["ipa"].startswith("[")


def test_carta_command(capsys):
    assert cli.main(["carta"]) == 0
    assert "С разбором:" in capsys.readouterr().out
    assert cli.main(["carta", "la casa"]) == 0
    assert "дом" in capsys.readouterr().out
