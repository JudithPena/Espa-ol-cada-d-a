"""Юнит NN: покрытие источника, контракт данных, сохранность предыдущих юнитов."""
import hashlib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 63
# Сколько пунктов в каждом упражнении страницы-источника: NN.1, NN.2, …
SOURCE_ITEMS = [7, 7, 25]
# Пункты источника, которые не стали вопросами: причина из реестра в отчёте юнита.
NOT_TRANSFERRED = {"63.1.1": "Заполненный образец источника сохранён в preview упражнения 63.1.", "63.2.1": "Заполненный образец источника сохранён в preview упражнения 63.2.", "63.3.1": "Заполненный образец источника сохранён в preview упражнения 63.3."}
PLAIN_TEXT = ("prompt", "context", "explain", "translation", "answerHint")


def unit():
    return next(u for u in load_grammar() if u["number"] == NUMBER)


def test_previous_units_are_untouched():
    before = json.loads(Path(f"tests/data/grammar_before_unit{NUMBER}.json").read_text(encoding="utf-8"))
    assert len(before) == len([p for p in GRAMMAR.glob("[0-9]*.json") if int(p.name[:3]) < NUMBER])
    for name, digest in before.items():
        data = (GRAMMAR / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == digest, name


def test_every_source_item_is_accounted_for():
    refs = [q["sourceRef"] for g in unit()["exercises"] for q in g["questions"]]
    assert all(refs), "у каждого вопроса упражнения есть sourceRef"
    used = [r for r in refs if r != "extra"]
    assert len(used) == len(set(used)), "один пункт источника не переносится дважды"
    covered = set()
    for r in used:
        base, *more = re.sub(r"[a-z]$", "", r).split("+")
        covered.add(base)
        covered.update(base.rsplit(".", 1)[0] + "." + n for n in more)
    expected = {f"{NUMBER}.{g}.{i}" for g, count in enumerate(SOURCE_ITEMS, 1) for i in range(1, count + 1)}
    assert not covered & set(NOT_TRANSFERRED)
    assert covered | set(NOT_TRANSFERRED) == expected
    assert all(len(reason) >= 15 for reason in NOT_TRANSFERRED.values())


def test_unit_contract():
    u = unit()
    assert u["id"] == next(GRAMMAR.glob(f"{NUMBER:03d}_*.json")).stem
    assert u["learningOrder"][-1] == "summary"
    for section in u["sections"]:
        check = section["check"]
        assert check["title"] == "Мини-проверка" and check["instruction"].strip()
        assert len(check["questions"]) == 3 and "inputFormat" not in check
        for q in check["questions"]:
            assert len(q.get("options", [])) >= 2 and set(q["options"]) - set(q["answers"]), q["prompt"]
    for group in [s["check"] for s in u["sections"]] + u["exercises"]:
        for q in group["questions"]:
            assert q.get("context") and q.get("learningAction")
            for field in PLAIN_TEXT:
                assert "`" not in q.get(field, "") and "**" not in q.get(field, ""), (group["id"], field)
            if q.get("options"):
                assert 2 <= len(q["options"]) <= 6
            typed = not q.get("options") and not q.get("tiles") and not q.get("guidedGaps")
            if typed:
                fmt = q.get("inputFormat") or group.get("inputFormat")
                assert fmt and fmt["instruction"] and fmt["placeholder"], group["id"]
                assert "".join(q["inputChars"]) == "áéíóúüñ"
                assert q.get("accentPolicy") or group.get("accentPolicy"), "режим ударений задан явно"
    for group in u["exercises"]:
        assert group["theorySections"] and 3 <= len(group["questions"]) <= 15
        assert group["title"].startswith(group["id"] + " · ")


def test_report_exists():
    assert Path(f"docs/grammar_units/{NUMBER:02d}.md").exists()
def by_ref(ref):
    return next(q for g in unit()["exercises"] for q in g["questions"] if q["sourceRef"] == ref)


def test_forms_and_irregulars():
    assert by_ref("63.1.2")["answers"] == ["eran llevaban escuchaban"]
    assert by_ref("63.1.6")["answers"] == ["vivíamos íbamos"]
    assert by_ref("63.1.7")["answers"] == ["querías Quería"]
    assert by_ref("63.1.4b")["answers"] == ["se duchaba se hacía"]
    assert by_ref("63.2.7")["answers"] == ["eran"]
    assert by_ref("63.3.5+6")["answers"] == ["Tenía había"]


def test_merged_blanks_have_matching_gaps():
    for g in unit()["exercises"]:
        for q in g["questions"]:
            if "+" in q["sourceRef"]:
                assert len(q["gapParts"]) - 1 == len(q["sourceRef"].split("+"))
            if q.get("gapParts"):
                assert all(sum(q["gapWordCounts"]) == len(a.split()) for a in q["answers"])


def test_narrator_alternative_and_strict_accents():
    assert by_ref("63.3.22+23")["answers"] == ["bailábamos gustaba", "bailaban gustaba"]
    u = unit()
    assert all(g.get("accentPolicy") == "strict" for g in u["exercises"])
    fixes = [q for q in u["exercises"][0]["questions"] if q["learningAction"] == "исправление ошибки"]
    assert [q["answers"][0] for q in fixes] == ["veía", "íbamos", "trabajabais"]


def test_word_banks_and_variety():
    u = unit()
    assert all(u["exercises"][i].get("vocabulary") for i in (1, 2, 3))
    qs = [q for g in u["exercises"] for q in g["questions"]]
    assert len(qs) == 36 and sum(bool(q.get("tiles")) for q in qs) == 2
    assert len({q["learningAction"] for q in qs}) >= 4
