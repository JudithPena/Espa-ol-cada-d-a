"""Модель доводки A0–A1 (docs/a0_a1_fixes_plan.md): id блоков, источник и правило задания, навыки, версии.

Только уроки сайта: уроки канала эти поля не используют, их разбор и рендер не меняются.
"""

from pathlib import Path

import pytest
import yaml

from espanol.course import ContentError, load_course, parse_block, parse_lesson
from espanol.lexicon import Lexicon
from espanol.scenario import check, screen_warnings
from espanol.site import lesson_data, site_data
from espanol.wordcards import load_cards

CONTENT = Path(__file__).resolve().parent.parent / "content"


def _course(tmp_path, lessons, skills=None):
    (tmp_path / "units").mkdir()
    (tmp_path / "course.yaml").write_text(yaml.safe_dump({"title": "t", "names": {"female": ["Ana", "Lucía"], "male": ["Pablo"]}},
                                                         allow_unicode=True), encoding="utf-8")
    if skills is not None:
        (tmp_path / "skills.yaml").write_text(yaml.safe_dump(skills, allow_unicode=True), encoding="utf-8")
    base = {"id": "base", "number": 0, "level": "A0", "title": "База", "lessons": [
        {"id": "w", "kind": "vocab", "vocab": ["el café — кофе", "sí — да", "no — нет", "gracias — спасибо",
                                               "bien — хорошо", "mal — плохо", "regular — так себе"]}]}
    unit = {"id": "u", "number": 1, "level": "A0", "title": "Тема", "lessons": lessons}
    for name, data in (("00_base.yaml", base), ("01_u.yaml", unit)):
        (tmp_path / "units" / name).write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return load_course(tmp_path)


def _mk(path):
    path.mkdir()


def _messages(course):
    lexicon = Lexicon(course)
    return [i.message for i in check(course, lexicon)]


DIALOGUES = [
    {"dialogue": {"id": "morning", "title": "Утром", "lines": ["Ana: Bien, gracias. | Хорошо, спасибо."]}},
    {"dialogue": {"id": "evening", "title": "Вечером", "lines": ["Ana: Regular. | Так себе."]}},
]


def test_meta_fields_are_parsed_for_site_blocks():
    b = parse_block({"rule": {"id": "r1", "text": "Правило."}}, "t")
    assert b.type == "rule" and b.data == "Правило." and b.meta == {"id": "r1"}
    b = parse_block({"dialogue": {"id": "d1", "lines": ["Ana: Sí. | Да."]}}, "t")
    assert b.meta["id"] == "d1" and b.data["lines"] == [("Ana", "Sí.", "Да.")]
    b = parse_block({"choose": {"source": "d1", "skill": "x", "items": [
        {"q": "?", "options": "a | b", "free": True, "rule": "r1", "mistakes": {"b": "почему не b"}}]}}, "t")
    assert b.meta == {"source": "d1", "skill": ["x"]}
    assert b.data["items"][0]["meta"] == {"free": True, "rule": "r1", "mistakes": {"b": "почему не b"}}
    b = parse_block({"text": {"text": "Новый экран.", "slide": "new"}}, "t")
    assert b.meta == {"slide": "new"}
    b = parse_block({"write": {"items": [{"say": "uno", "a": "1", "noaudio": {"q": "uno — цифрой", "a": "1"}}]}}, "t")
    assert b.data["items"][0]["noaudio"]["answers"] == ["1"]
    assert parse_block({"recap": {"phrase": "Sí, gracias."}}, "t").data == {"title": "", "words": True, "phrase": "Sí, gracias."}
    assert parse_block({"review": {"skills": ["x"], "n": 2}}, "t").data["n"] == 2
    with pytest.raises(ContentError):
        parse_block({"review": {"skills": ["x"], "n": 5}}, "t")
    with pytest.raises(ContentError):
        parse_block({"choose": {"source": "d", "free": True, "items": [{"q": "?", "options": "a | b"}]}}, "t")
    with pytest.raises(ContentError):
        parse_block({"text": {"text": "x", "slide": "old"}}, "t")


def test_explicit_source_is_required_after_a_source_in_reworked_lessons(tmp_path):
    lesson = {"id": "l", "kind": "dialogue", "version": 2, "goal": "g", "blocks": [
        *DIALOGUES,
        {"choose": {"items": [{"q": "Как дела у Аны утром?", "options": "Bien. | Mal."}]}},
        {"choose": {"items": [{"q": "Как дела у Аны вечером?", "options": "Regular. | Bien.", "source": "evening"}]}},
        {"choose": {"free": True, "items": [{"q": "Как сказать «хорошо»?", "options": "bien | mal"}]}},
    ]}
    msgs = _messages(_course(tmp_path, [lesson]))
    assert any("укажите source" in m and "утром" in m for m in msgs)
    assert not any("вечером" in m for m in msgs)
    assert not any("хорошо" in m for m in msgs)


def test_old_lessons_keep_working_without_explicit_source(tmp_path):
    lesson = {"id": "l", "kind": "dialogue", "goal": "g", "blocks": [
        *DIALOGUES, {"choose": {"items": [{"q": "Как дела у Аны утром?", "options": "Bien. | Mal."}]}}]}
    assert not any("source" in m for m in _messages(_course(tmp_path, [lesson])))


def test_references_resolve_to_the_right_kind_of_block(tmp_path):
    lesson = {"id": "l", "kind": "dialogue", "version": 2, "goal": "g", "blocks": [
        {"rule": {"id": "r", "text": "Правило."}},
        *DIALOGUES,
        {"choose": {"items": [
            {"q": "1", "options": "Bien. | Mal.", "source": "nope"},
            {"q": "2", "options": "Bien. | Mal.", "source": "r"},
            {"q": "3", "options": "Bien. | Mal.", "free": True, "rule": "morning"},
            {"q": "4", "options": "Bien. | Mal.", "free": True, "skill": "nada"},
        ]}},
    ]}
    msgs = _messages(_course(tmp_path, [lesson], skills={}))
    assert any("source «nope»" in m for m in msgs)
    assert any("source «r»" in m and "источник" in m for m in msgs)
    assert any("rule «morning»" in m for m in msgs)
    assert any("навыка «nada» нет" in m for m in msgs)


def test_site_data_resolves_sources_rules_and_skills(tmp_path):
    lesson = {"id": "l", "kind": "dialogue", "version": 2, "check": "soft", "goal": "g", "blocks": [
        "Вступление.",
        {"rule": {"id": "r", "text": "Правило про bien."}},
        {"choose": {"items": [{"q": "bien?", "options": "хорошо | плохо", "skill": "s"}]}},
        *DIALOGUES,
        {"choose": {"source": "evening", "items": [{"q": "Вечером?", "options": "Regular. | Bien."},
                                                   {"q": "Утром?", "options": "Bien. | Mal.", "source": "morning"}]}},
        {"choose": {"free": True, "items": [{"q": "Как сказать «плохо»?", "options": "mal | bien", "rule": "r"}]}},
    ]}
    course = _course(tmp_path, [lesson], skills={"s": {"title": "bien и mal", "lesson": "u/l"}})
    assert _messages(course) == []
    L = lesson_data(course.lessons[1], {})
    blocks = L["blocks"]
    kinds = [b["t"] for b in blocks]
    morning, evening = kinds.index("dialogue"), len(kinds) - 1 - kinds[::-1].index("dialogue")
    first, ctx, free = [b for b in blocks if b["t"] == "choose"]
    assert first["items"][0]["rule"] == [kinds.index("rule")]           # правило того же витка
    assert first["items"][0]["skill"] == ["s"]
    assert ctx["items"][0]["src"] == evening and ctx["items"][1]["src"] == morning   # каждый вопрос — к своему диалогу
    assert ctx["items"][0]["rule"] == []                                 # после диалога правила того витка нет
    assert free["items"][0]["free"] and "src" not in free["items"][0] and free["items"][0]["rule"] == [kinds.index("rule")]
    assert L["version"] == 2 and L["check"] == "soft"
    assert "ctx" not in ctx    # у перестроенного урока источник только явный


def test_skill_must_be_introduced_before_use_and_have_free_material(tmp_path):
    lessons = [
        {"id": "a", "kind": "vocab", "version": 2, "goal": "g", "blocks": [
            {"choose": {"skill": "late", "items": [{"q": "bien?", "options": "хорошо | плохо"}]}}]},
        {"id": "b", "kind": "practice", "version": 2, "goal": "g", "blocks": [
            {"mission": {"id": "m", "title": "M", "text": "Вы — Ана."}},
            {"choose": {"source": "m", "skill": "ctx_only", "items": [{"q": "?", "options": "Bien. | Mal."}]}}]},
    ]
    msgs = _messages(_course(tmp_path, lessons, skills={"late": {"title": "x", "lesson": "u/b"}, "ctx_only": {"title": "y", "lesson": "u/a"}}))
    assert any("«late» вводится позже" in m for m in msgs)
    assert any("«ctx_only» нет ни одного самостоятельного" in m for m in msgs)


def test_every_word_is_checked_or_recapped(tmp_path):
    lesson = {"id": "l", "kind": "vocab", "version": 2, "goal": "g", "vocab": ["hola — привет", "adiós — пока"],
              "blocks": [{"learn": ["hola", "adiós"]}, {"choose": {"items": [{"q": "Привет?", "options": "Hola. | Adiós."}]}}]}
    msgs = _messages(_course(tmp_path, [lesson]))
    assert any("«adiós» не проверяется" in m for m in msgs) and not any("«hola»" in m for m in msgs)
    lesson["blocks"].append({"recap": {}})
    assert not any("не проверяется" in m for m in (_mk(tmp_path / "2"), _messages(_course(tmp_path / "2", [lesson])))[1])


def test_screen_warnings_for_reworked_lessons(tmp_path):
    long = "Очень длинное объяснение. " * 50
    lesson = {"id": "l", "kind": "grammar", "version": 2, "goal": "g", "blocks": [
        {"header": "Заголовок"}, {"choose": {"free": True, "items": [{"q": "bien?", "options": "хорошо | плохо"}]}},
        long, {"choose": {"items": [{"q": "mal?", "options": "плохо | хорошо"}]}}]}
    warns = [w.message for w in screen_warnings(_course(tmp_path, [lesson]))]
    assert any("почти пустой" in w for w in warns) and any("знаков" in w for w in warns)


def test_lesson_version_and_check_are_validated():
    from espanol.course import Unit
    unit = Unit(id="u", number=1, level="A0", title="t", goals=[])
    assert parse_lesson({"id": "l", "kind": "vocab"}, unit, "t").version == 1
    assert parse_lesson({"id": "l", "kind": "quiz", "version": 2, "check": "control"}, unit, "t").check == "control"
    with pytest.raises(ContentError):
        parse_lesson({"id": "l", "kind": "quiz", "check": "hard"}, unit, "t")


def test_site_data_has_skill_registry():
    data = site_data(load_course(CONTENT / "site"), load_cards(CONTENT), units={1})
    assert isinstance(data["skills"], dict)
    assert all("version" in L and "check" in L for L in data["lessons"])
