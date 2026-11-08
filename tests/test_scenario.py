"""Сценарии уроков сайта (content/site): новые блоки, проверки порядка и заданий, совместимость прогресса."""

import json
from pathlib import Path

import pytest
import yaml

from espanol.course import SITE_ONLY_BLOCKS, ContentError, load_course, parse_block, parse_lesson
from espanol.lexicon import Lexicon
from espanol.scenario import channel_issues, check
from espanol.site import site_data
from espanol.site_audio import audio_texts
from espanol.wordcards import load_cards

CONTENT = Path(__file__).resolve().parent.parent / "content"
SITE = CONTENT / "site"


@pytest.fixture(scope="module")
def site():
    return load_course(SITE)


def _course(tmp_path, lessons, unit_extra=None):
    """Маленький курс сайта во временной папке: тема 0 (известные слова) и тема 1 с уроками из теста."""
    (tmp_path / "units").mkdir()
    (tmp_path / "course.yaml").write_text(yaml.safe_dump({"title": "t", "names": {"female": ["Ana"], "male": ["Pablo"]}}, allow_unicode=True), encoding="utf-8")
    base = {"id": "base", "number": 0, "level": "A0", "title": "База", "lessons": [
        {"id": "w", "kind": "vocab", "vocab": ["el café — кофе", "sí — да", "no — нет", "gracias — спасибо"]}]}
    later = {"id": "later", "number": 2, "level": "A0", "title": "Позже", "lessons": [
        {"id": "w", "kind": "vocab", "vocab": ["la cerveza — пиво"]}]}
    unit = {"id": "u", "number": 1, "level": "A0", "title": "Тема", "lessons": lessons, **(unit_extra or {})}
    for name, data in (("00_base.yaml", base), ("01_u.yaml", unit), ("02_later.yaml", later)):
        (tmp_path / "units" / name).write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return load_course(tmp_path)


def _messages(course):
    lexicon = Lexicon(course)
    return [i.message for i in lexicon.check() + check(course, lexicon)]


def test_parse_scenario_blocks():
    b = parse_block({"learn": ["el café", "la casa"]}, "t")
    assert b.type == "learn" and b.data == ["el café", "la casa"]
    b = parse_block({"choose": {"title": "T", "items": [{"q": "¿?", "options": "a | b | c", "explain": "e",
                                                          "lines": ["Ana: ¡Hola! | Привет!"], "say": "hola"}]}}, "t")
    it = b.data["items"][0]
    assert it["options"] == ["a", "b", "c"] and it["lines"] == [("Ana", "¡Hola!", "Привет!")] and it["say"] == "hola"
    b = parse_block({"write": {"format": "артикль", "items": ["___ libro => el", {"q": "x", "a": ["la casa", "una casa"]}]}}, "t")
    assert b.data["items"][0]["answers"] == ["el"] and b.data["items"][1]["answers"] == ["la casa", "una casa"]
    assert b.data["format"] == "артикль" and b.data["accents"] == "soft"
    b = parse_block({"match": ["sí — да", "no — нет"]}, "t")
    assert b.data["pairs"] == [("sí", "да"), ("no", "нет")]
    b = parse_block({"sort": {"el": ["libro"], "la": ["mesa", "casa"]}}, "t")
    assert b.data["groups"] == [("el", ["libro"]), ("la", ["mesa", "casa"])]
    b = parse_block({"build": ["Sí, gracias. — Да, спасибо.", {"es": "a b c", "ru": "x", "alt": "c b a", "extra": ["d"]}]}, "t")
    assert b.data["items"][0] == {"es": "Sí, gracias.", "ru": "Да, спасибо.", "alt": [], "extra": []}
    assert b.data["items"][1]["alt"] == ["c b a"] and b.data["items"][1]["extra"] == ["d"]
    assert parse_block({"mission": {"title": "M", "text": "t"}}, "t").data == {"title": "M", "text": "t"}
    assert parse_block({"more": "текст"}, "t").data["title"] == "Подробнее"
    with pytest.raises(ContentError):
        parse_block({"choose": {"items": [{"q": "без вариантов"}]}}, "t")
    with pytest.raises(ContentError):
        parse_block({"write": {"accents": "maybe", "items": ["a => b"]}}, "t")


def test_scripted_lessons(tmp_path):
    course = _course(tmp_path, [
        {"id": "old", "kind": "vocab", "vocab": ["la casa — дом"], "blocks": ["Текст.", {"exercise": ["casa => дом"]}]},
        {"id": "new", "kind": "vocab", "goal": "называть дом", "vocab": ["el perro — собака"],
         "blocks": [{"learn": ["el perro"]}, {"choose": {"items": [{"q": "Собака", "options": "el perro | el café"}]}}]},
    ])
    old, new = course.lesson("u/old"), course.lesson("u/new")
    assert not old.scripted and new.scripted and new.goal == "называть дом"
    assert _messages(course) == []


def test_task_before_its_card_is_an_error(tmp_path):
    course = _course(tmp_path, [{"id": "l", "kind": "vocab", "vocab": ["el perro — собака", "la casa — дом"], "blocks": [
        {"learn": ["el perro"]},
        {"choose": {"items": [{"q": "Дом", "options": "la casa | el perro"}]}},   # casa ещё не показана
        {"learn": ["la casa"]},
    ]}])
    assert any("раньше карточки слова «la casa»" in m for m in _messages(course))


def test_learn_portions_cover_all_words_once(tmp_path):
    course = _course(tmp_path, [{"id": "l", "kind": "vocab", "vocab": ["el perro — собака", "la casa — дом", "el gato — кот"],
                                 "blocks": [{"learn": ["el perro", "el perro", "la mesa"]}, {"write": ["Собака => el perro"]}]}])
    msgs = _messages(course)
    assert any("стоит в двух порциях" in m for m in msgs)
    assert any("«la mesa» нет среди слов урока" in m for m in msgs)
    assert any("«la casa» не стоит ни в одной порции" in m for m in msgs)


def test_task_structure_checks(tmp_path):
    course = _course(tmp_path, [{"id": "l", "kind": "practice", "blocks": [
        {"choose": {"items": [{"q": "a", "options": "sí"}, {"q": "b", "options": "sí | sí"}]}},
        {"match": ["sí — да", "sí — нет"]},
        {"sort": {"a": ["sí"], "b": []}},
        {"build": [{"es": "sí no", "ru": "x", "alt": ["no café"]}]},
        {"mission": "Ситуация без заданий после неё."},
    ]}])
    msgs = _messages(course)
    for part in ("нужно от 2 до", "одинаковые варианты", "стороны пар повторяются", "непустых групп",
                 "из тех же плиток", "после миссии нужно"):
        assert any(part in m for m in msgs), part


def test_vocabulary_of_tasks_is_checked(tmp_path):
    course = _course(tmp_path, [{"id": "l", "kind": "practice", "blocks": [
        {"write": [{"q": "Пиво", "a": "la cerveza"}]},                                      # слово темы 2
        {"choose": {"items": [{"q": "Кофе", "options": "el café | la cerveza | el cafés"}]}},  # позже + нарочно неверное
    ]}])
    msgs = _messages(course)
    assert any("незнакомое слово «cerveza»" in m for m in msgs)
    assert any("«cerveza» вводится позже" in m and "неверный вариант" in m for m in msgs)
    assert not any("cafés" in m for m in msgs)   # нарочно неверная форма — не ошибка


def test_site_content_is_valid(site):
    lexicon = Lexicon(site)
    assert [str(i) for i in check(site, lexicon)] == []
    assert [str(i) for i in lexicon.check()] == []


def test_channel_has_no_site_blocks(course, tmp_path):
    assert channel_issues(course) == []
    bad = _course(tmp_path, [{"id": "l", "kind": "practice", "blocks": [{"write": ["Кофе => el café"]}]}])
    assert channel_issues(bad) and SITE_ONLY_BLOCKS >= {"learn", "choose", "write", "match", "sort", "build", "mission", "more", "compare"}


def test_lesson_ids_and_order_unchanged(site):
    """Прогресс учеников хранится по id уроков: перестройка их не меняет и не переставляет."""
    ids = json.loads((Path(__file__).parent / "data" / "site_lesson_ids.json").read_text(encoding="utf-8"))
    assert [lesson.id for lesson in site.lessons] == ids
    assert len(site.units) == 24


def test_site_data_of_scenario(site):
    data = site_data(site, load_cards(CONTENT), units={1})
    lessons = {x["id"]: x for x in data["lessons"]}
    first = lessons["saludos/vocab1"]
    assert first["scripted"] and first["goal"]
    kinds = [b["t"] for b in first["blocks"]]
    assert kinds.index("learn") < kinds.index("choose") < len(kinds) - 1
    learn = [b for b in first["blocks"] if b["t"] == "learn"]
    assert [w for b in learn for w in b["words"]] == [w["es"] for w in first["words"]]
    choose = next(b for b in first["blocks"] if b["t"] == "choose")
    assert choose["items"][0]["o"][0][1] == "¡Buenos días!"   # первый вариант — верный, страница перемешивает
    write = next(b for b in first["blocks"] if b["t"] == "write")
    assert write["items"][0]["a"][0] == "Buenos días" and write["items"][0]["format"]
    # Все 24 темы собираются, уроки идут по порядку без пропусков.
    full = site_data(site, load_cards(CONTENT))
    assert [x["n"] for x in full["lessons"]] == list(range(1, len(site.lessons)))
    json.dumps(full, ensure_ascii=False)


def test_scenario_audio(site):
    """Каждая фраза, которую страница проиграет в задании сценария, есть в записи — по тому же ключу, по которому
    её ищет страница: вопрос на слух, верный вариант, любой допустимый ответ ввода, реплика-контекст голосом
    персонажа («@голос|текст»), стороны пар и карточки групп, фраза и каждое её слово в любом допустимом порядке."""
    import re as _re

    data = site_data(site, load_cards(CONTENT))
    texts = audio_texts(data)
    clean = lambda t: " ".join(str(t).split())
    spanish = lambda t: bool(_re.search("[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", t)) and not _re.search("[А-Яа-яЁё]", t)
    want = set()
    for lesson in data["lessons"]:
        for b in lesson["blocks"]:
            t = b["t"]
            if t == "choose":
                for it in b["items"]:
                    want |= {clean(it["say"])} - {""}
                    if spanish(it["o"][0][1]):
                        want.add(clean(it["o"][0][1]))
                    want |= {f"@{it['cast'][line[0]]['v']}|{clean(line[3])}" for line in it["lines"]}
            elif t == "write":
                for it in b["items"]:
                    want |= {clean(it["say"])} - {""}
                    want |= {clean(a) for a in it["a"] if spanish(a)}
            elif t == "match":
                want |= {clean(x) for p in b["pairs"] for x in p[2:] if x}
            elif t == "sort":
                want |= {clean(say) for _, items in b["groups"] for _, say in items if say}
            elif t == "build":
                for it in b["items"]:
                    for es in [it["es"], *it["alt"]]:
                        want.add(clean(es))
                        want |= {tok for tok in es.split(" ") if spanish(tok)}
    assert not [k for k in texts if not _re.search("[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", k.rpartition("|")[2])]   # русское не записываем
    missing = sorted(want - set(texts))
    assert not missing, missing[:10]
    assert "@" in next(k for k in texts if k.startswith("@"))   # реплики-контекст — голосом персонажа
    assert not any("доброе утро" in k for k in texts)        # русская сторона пары не озвучивается


def test_recall_skips_context_bound_tasks(site):
    """«Вспомним» и «Фразы и конструкции» не берут вопросы к диалогу, тексту и миссии своего урока."""
    data = site_data(site, load_cards(CONTENT))
    for lesson in data["lessons"]:
        ctx = mission = False
        for b in lesson["blocks"]:
            if b["t"] == "mission":
                mission = True
            if b["t"] in ("dialogue", "reading", "mission"):
                ctx = True
            elif b["t"] in ("learn", "rule", "compare", "table", "header", "examples", "conjugation", "list"):
                ctx = mission
            if b["t"] in ("choose", "write"):
                assert bool(b.get("ctx")) == ctx, (lesson["id"], b["t"], b.get("title"))
    flagged = [b for x in data["lessons"] for b in x["blocks"] if b.get("ctx")]
    free = [b for x in data["lessons"] for b in x["blocks"] if b["t"] in ("choose", "write") and not b.get("ctx")]
    assert flagged and len(free) > len(flagged) / 2


def test_rebuilt_course_standard(site):
    """Стандарт перестройки A0–A1 (docs/site_lessons_guide.md): короткие порции слов, микроцель у каждого
    урока-сценария, ни одного упражнения с автодистракторами и задания-самопроверки, верный вариант не выдаёт себя длиной."""
    from espanol.markup import plain

    for lesson in site.lessons:
        types = {b.type for b in lesson.blocks}
        assert not types & {"exercise", "task"}, f"{lesson.id}: старые блоки exercise/task"
        if lesson.scripted:
            assert lesson.goal, f"{lesson.id}: нет goal"
            assert all(len(b.data) <= 6 for b in lesson.blocks if b.type == "learn"), lesson.id
        elif lesson.kind not in ("intro", "quiz", "final"):
            raise AssertionError(f"{lesson.id}: урок не переписан сценарием")
    for unit in site.units:
        items = [it for L in unit.lessons for b in L.blocks if b.type == "choose" for it in b.data["items"]]
        if len(items) < 5:
            continue
        longest = sum(1 for it in items if (lens := [len(plain(o)) for o in it["options"]])[0] == max(lens) and lens.count(max(lens)) == 1)
        assert longest / len(items) <= 0.6, f"тема {unit.number}: верный вариант самый длинный в {longest} из {len(items)}"
