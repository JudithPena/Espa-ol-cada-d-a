import json
from pathlib import Path

from espanol.site import BUILD_MAX, BUILD_MIN, build_site, parse_units, site_data
from espanol.wordcards import load_cards

CONTENT = Path(__file__).resolve().parent.parent / "content"


def test_parse_units():
    assert parse_units(None) is None
    assert parse_units("0-2,5") == {0, 1, 2, 5}


def test_site_data_covers_course(course):
    data = site_data(course, load_cards(CONTENT))
    assert len(data["lessons"]) == len(course.lessons)
    assert [lesson["n"] for lesson in data["lessons"]] == list(range(len(course.lessons)))
    json.dumps(data, ensure_ascii=False)


def test_lesson_content(course):
    data = site_data(course, load_cards(CONTENT), units={1})
    assert {lesson["unit"] for lesson in data["lessons"]} == {1}
    vocab = data["lessons"][0]
    hola = next(w for w in vocab["words"] if w["es"] == "buenos días")
    assert hola["ru"].startswith("доброе утро") and hola["pron"] and hola["ex"]
    assert all(b["t"] != "words" for lesson in data["lessons"] for b in lesson["blocks"])
    exercise = next(b for b in vocab["blocks"] if b["t"] == "exercise")
    assert exercise["items"][0]["ap"] == "¡Buenos días!"
    for lesson in data["lessons"]:
        for es, ru in lesson["sentences"]:
            assert BUILD_MIN <= len(es.split()) <= BUILD_MAX and ru


def test_cards_from_repaso(course):
    data = site_data(course, load_cards(CONTENT), units={0})
    hola = data["lessons"][0]["words"][0]
    assert hola["es"] == "¡Hola!" and hola["meaning"] and hola["trap"]


def test_build_site(course, tmp_path):
    out = build_site(course, load_cards(CONTENT), tmp_path / "index.html", units={0})
    page = out.read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>") and "/*__DATA__*/" not in page
    assert '"title": "Español cada día"' in page
    fragment = build_site(course, load_cards(CONTENT), tmp_path / "f.html", units={0}, fragment=True)
    assert fragment.read_text(encoding="utf-8").startswith("<title>")
