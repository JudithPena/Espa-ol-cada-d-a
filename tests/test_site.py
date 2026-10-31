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
    assert len(data["lessons"]) == len(course.lessons) - 1
    assert [lesson["n"] for lesson in data["lessons"]] == list(range(1, len(course.lessons)))
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
    # Вводного урока о канале на сайте нет, его «¡Hola!» — первое слово следующего урока.
    first = data["lessons"][0]
    assert first["kind"] != "intro" and first["n"] == 1
    hola = first["words"][0]
    assert hola["es"] == "¡Hola!" and hola["meaning"] and hola["trap"]


def test_build_site(course, tmp_path):
    out = build_site(course, load_cards(CONTENT), tmp_path / "index.html", units={0})
    page = out.read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>") and "/*__DATA__*/" not in page
    assert '"title": "Español cada día"' in page
    fragment = build_site(course, load_cards(CONTENT), tmp_path / "f.html", units={0}, fragment=True)
    assert fragment.read_text(encoding="utf-8").startswith("<title>")


def test_word_forms(course):
    from espanol.site import word_forms

    forms = word_forms(course)
    assert forms["tengo"] == "tener" and forms["soy"] == "ser"
    assert forms["casas"] == "la casa" and forms["alta"] == "alto/a"
    assert "la" not in forms and "de" not in forms  # артикли и предлоги из фраз не открывают фразу


def test_no_transcription_choice(course):
    """Выбор транскрипции на сайте не задаём, произношение проверяется на слух."""
    data = site_data(course, load_cards(CONTENT), units={0})
    exercises = [it for lesson in data["lessons"] for b in lesson["blocks"] if b["t"] == "exercise" for it in b["items"]]
    assert exercises and not any("[" in it["ap"] for it in exercises)
    assert any(it["qp"] == "la plaza" and it["ap"] == "площадь" for it in exercises)  # перевод остаётся
    questions = [q["q"] for lesson in data["lessons"] for q in lesson["quiz"]]
    assert "Как читается «queso»?" not in questions and "Как читается «vino»?" not in questions
    assert "Где ударение в слове «hotel»?" in questions  # правила ударения остаются


def test_stress_questions(course):
    """Где ударение видно по значку ´, не спрашиваем; варианты — то же слово с ударением на разных слогах."""
    from espanol.site import stress_options

    assert stress_options("ho-TEL") == ["HO-tel", "ho-TEL"]
    assert stress_options("la casa") is None
    data = site_data(course, load_cards(CONTENT), units={0})
    questions = [q["q"] for lesson in data["lessons"] for q in lesson["quiz"]]
    assert not any("café" in q or "música" in q for q in questions)
    stress = {it["qp"]: it for lesson in data["lessons"] for b in lesson["blocks"] if b["t"] == "exercise"
              for it in b["items"] if "opts" in it}
    assert set(stress) == {"la casa", "el hotel", "el taxi"}
    assert stress["la casa"]["opts"] == ["CA-sa", "ca-SA"]


def test_without_telegram():
    """На сайте нет спойлеров, опросов и комментариев: такие предложения и задания убираются."""
    from espanol.site import without_telegram

    assert without_telegram("Давайте проверим, как вы освоили чтение. Ответ спрятан под спойлером.") == (
        "Давайте проверим, как вы освоили чтение.")
    assert without_telegram("Спасибо, что учились с нами! Напишите в комментариях, что понравилось. "
                            "Можно начать так: _Me ha encantado..._") == "Спасибо, что учились с нами!"
    assert "вопрос" in without_telegram("Задайте вопрос **¿Cómo estás?** другу, а потом ответьте сами.")


def test_no_comment_tasks(course):
    data = site_data(course, load_cards(CONTENT))
    texts = [b.get("html", "") for lesson in data["lessons"] for b in lesson["blocks"]]
    assert not any("комментари" in t or "спойлер" in t for t in texts)


def test_word_phrases(course):
    """Фразы курса ищутся целиком, длинные раньше коротких; фразы с пропуском не ищем."""
    from espanol.site import word_phrases

    phrases = {" ".join(words): es for words, es in word_phrases(course)}
    assert phrases["buenos días"] == "buenos días" and phrases["qué tal"] == "¿Qué tal?"
    assert phrases["cómo está usted"] == "¿Cómo está usted?"
    assert not any("dice en" in p for p in phrases)  # «¿Cómo se dice... en español?»
    lengths = [len(" ".join(w)) for w, _ in word_phrases(course)]
    assert lengths == sorted(lengths, reverse=True)
