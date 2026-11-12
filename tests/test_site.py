import json
from pathlib import Path

from espanol.course import load_course
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
    assert "/*__GRAMMAR_PLAYER__*/" not in page and "function gPlayerView(" in page
    assert '"title": "Español cada día"' in page
    fragment = build_site(course, load_cards(CONTENT), tmp_path / "f.html", units={0}, fragment=True)
    assert fragment.read_text(encoding="utf-8").startswith("<title>")


def test_theory_art_is_served_on_demand_but_fragments_remain_portable(course, tmp_path):
    import base64
    from espanol.grammar import load_grammar

    art = [s["illustration"] for u in load_grammar() for s in u["sections"] if s.get("illustration")]
    assert len(art) == 45
    out = build_site(course, load_cards(CONTENT), tmp_path / "index.html", units={0})
    page = out.read_text(encoding="utf-8")
    assets = {p.read_bytes(): p.relative_to(tmp_path).as_posix() for p in (tmp_path / "g").glob("*.webp")}
    assert len(assets) == 45
    for scene in art:
        data = base64.b64decode(scene["image"].split(",", 1)[1])
        resources = "\n".join(p.read_text() for p in (tmp_path / "d" / "grammar").rglob("*.json"))
        assert assets[data] in resources
        assert scene["image"] not in page

    fragment = build_site(course, load_cards(CONTENT), tmp_path / "embed.html", units={0}, fragment=True)
    embedded = fragment.read_text(encoding="utf-8")
    assert all(scene["image"] in embedded for scene in art)


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


def test_videos_on_site(course):
    """Разборы видео попадают на сайт: ссылка, фразы с новыми словами и переводом."""
    from espanol.videos import load_videos

    videos = load_videos(CONTENT, course)
    data = site_data(course, load_cards(CONTENT), units={0}, videos=videos)
    assert len(data["videos"]) == len(videos) >= 1
    first = data["videos"][0]
    assert first["url"].startswith("http") and first["segments"]
    seg = first["segments"][0]
    assert seg["es"] and seg["ru"] and seg["words"] and {"es", "ru", "say"} <= set(seg["words"][0])
    assert site_data(course, load_cards(CONTENT), units={0})["videos"] == []


def test_site_api(course):
    """Сайт знает адрес бота для входа через Telegram."""
    data = site_data(course, load_cards(CONTENT), units={0})
    assert data["api"].startswith("https://") and data["api"].endswith(".workers.dev")


def test_site_icons(course, tmp_path):
    """Рядом со страницей лежат иконки и манифест для установки на главный экран."""
    from espanol.site import build_site

    out = build_site(course, load_cards(CONTENT), tmp_path / "index.html", units={0})
    html = out.read_text(encoding="utf-8")
    assert 'rel="apple-touch-icon"' in html and 'rel="manifest"' in html
    for name in ("apple-touch-icon.png", "icon-192.png", "icon-512.png", "icon-maskable-512.png", "manifest.webmanifest"):
        assert (tmp_path / name).is_file(), name


def test_row_art(course):
    """Картинки к объяснению стоят в своей строке таблицы, рядом с поясняемой буквой."""
    from espanol.site import ROW_ART

    data = site_data(course, load_cards(CONTENT), units={0})
    lessons = {x["id"]: x for x in data["lessons"]}
    for lesson_id, by_cell in ROW_ART.items():
        table = next(b for b in lessons[lesson_id]["blocks"] if b["t"] == "table")
        assert len(table["rowpics"]) == len(by_cell)
        assert all(u.startswith("data:image/webp") for u in table["rowpics"].values())


def test_audio_texts(course):
    """Озвучка сайта: слова, примеры, реплики диалогов своим голосом, слова «Соберите фразу», разборы видео."""
    from espanol.site_audio import M, VOICES, audio_texts, file_id
    from espanol.videos import load_videos

    data = site_data(course, load_cards(CONTENT), videos=load_videos(CONTENT, course))
    texts = audio_texts(data)
    assert texts["la casa"][0] == "la casa" and texts["la casa"][1] in VOICES
    assert {v.partition("@")[0] for _, v in texts.values()} == set(VOICES)  # и женские, и мужской голос
    dialogue = [k for k in texts if k.startswith("@")]
    assert dialogue and all(k.startswith(f"@{texts[k][1]}|") for k in dialogue)   # ключ «@голос|текст»
    pablo = next(b for x in data["lessons"] for b in x["blocks"] if b["t"] == "dialogue" and "Pablo" in b["cast"])
    line = next(ln for ln in pablo["lines"] if ln[0] == "Pablo")
    assert texts[f"@{M}|{line[3]}"] == (line[3], M)
    sentence = next(x["sentences"][0][0] for x in data["lessons"] if x["sentences"])
    assert all(tok in texts for tok in sentence.split(" ") if any(ch.isalpha() for ch in tok))
    seg = data["videos"][0]["segments"][0]
    assert seg["es"] in texts
    assert all(not k.startswith(" ") and "  " not in k for k in texts)  # ключи — как clean() на странице
    assert file_id("la casa", VOICES[0]) != file_id("la casa", VOICES[1])
    assert file_id("la casa", M) != file_id("la casa", M + "@-14Hz")


def test_dialogue_cast():
    """У персонажа один голос во всех диалогах сайта, собеседники одного диалога звучат по-разному, мужчины — мужским голосом."""
    from espanol.site_audio import CAST, M, cast

    site = load_course(CONTENT / "site")
    seen: dict[str, str] = {}
    for lesson in site.lessons:
        for block in lesson.blocks:
            if block.type != "dialogue":
                continue
            names = list(dict.fromkeys(s for s, _, _ in block.data["lines"]))
            voices = cast(names)
            assert len({c["v"] for c in voices.values()}) == len(names), (lesson.id, names)
            for name, c in voices.items():
                assert name in CAST, f"{lesson.id}: у персонажа {name} нет голоса в site_audio.CAST"
                assert seen.setdefault(name, c["v"]) == c["v"]
                assert (c["g"] == "m") == c["v"].startswith(M)
    assert cast(["Marta", "Jorge", "Rosa"])["Jorge"]["v"].startswith(M)
    slugs = [a for _, _, a in CAST.values()]
    assert len(set(slugs)) == len(slugs) and all(slugs)          # у каждого персонажа свой аватар
    assert cast(["Lucía"])["Lucía"]["a"] == "lucia" and cast(["Marta"])["Marta"]["a"] == ""
    assert len({c["v"] for c in cast(["Marta", "Rosa"]).values()}) == 2


def test_site_note_drops_unknown_and_offtopic():
    from espanol.site import site_note

    unknown = lambda text: [w for w in ("caza", "tomar") if w in text]
    assert site_note("c перед a читается как «к». Не путайте с caza (с z) — «охота».", unknown) == "c перед a читается как «к»."
    assert site_note("x между гласными — «кс». В Латинской Америке «взять такси» — tomar un taxi 🌎.", unknown) == "x между гласными — «кс»."
    assert site_note("Не путайте с caza.", unknown) is None


def test_theory_italic_chips_pairs_and_steps():
    from espanol.course import Block
    from espanol.site import _block, _card, _italic_examples

    ex = _italic_examples("_¡Hola, buenos días!_, _¡Hola, buenas tardes!_")
    assert [e[1] for e in ex] == ["¡Hola, buenos días!", "¡Hola, buenas tardes!"]   # запятая внутри фразы не делит
    assert [e[1] for e in _italic_examples("_el libro, el cuaderno_")] == ["el libro", "el cuaderno"]
    assert _italic_examples("_Escucha, Pablo_ («Послушай, Пабло»)")[0][3] == "Послушай, Пабло"

    card, = _card("Поэтому _hasta luego_ дословно означает «до потом», то есть «до встречи», "
                  "а _hasta mañana_ означает «до завтра»: _¡Hasta luego, Pablo!_, _¡Hasta mañana, Carmen!_")
    assert [(p[1], p[3]) for p in card["pairs"]] == [("hasta luego", "до потом"), ("hasta mañana", "до завтра")]
    assert "до встречи" in card["pairs"][0][4] and len(card["ex"]) == 2 and card["html"] == ""

    lst = _block(Block("list", ["☀️ Утром говорят **buenos días**: _¡Buenos días!_, _¡Buenos días, María!_"]))
    assert lst["steps"][0]["icon"] == "☀️" and len(lst["steps"][0]["ex"]) == 2

    num = _block(Block("text", "1. Слово **hay** не меняется. _Hay un libro._ _Hay dos libros._\n2. Перед **hay** нет артикля."))
    assert len(num["items"]) == 2 and len(num["items"][0]["ex"]) == 2


def test_compare_block():
    from espanol.course import parse_block
    from espanol.site import _block

    b = parse_block({"compare": {"style": "small", "join": True, "cards": [
        {"head": "tú", "label": "«ты»", "ex": ["¿Y tú? — А ты?"]}, {"head": "¿ … ?", "label": "Вопрос"}]}}, "тест")
    d = _block(b)
    assert d["join"] and d["style"] == "small"
    assert d["cards"][0]["say"] == "tú" and d["cards"][1]["say"] == ""   # знаки без букв не озвучиваем
    assert d["cards"][0]["ex"][0][1:] == ["¿Y tú?", "", "А ты?"]


def test_word_note_levels():
    """Карточка слова: важное — «На заметку», остальное — «Подробнее», очевидное (род при артикле) — не показываем."""
    from espanol.site import note_levels

    assert note_levels("la mesa", "Женского рода: la mesa.", None, None) == (None, [])
    main, more = note_levels("la cerveza", "v читается как b: «сэрбэса», а не «сэрвэса».", "θ", None)
    assert main and more == [["Произношение", "θ"]]
    main, more = note_levels("trabajar", "Кем работаете — de: Trabajo de camarero.", None, None)
    assert main is None and more[0][0] == "Нюанс"
