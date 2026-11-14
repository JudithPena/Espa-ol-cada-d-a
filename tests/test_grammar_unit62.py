"""Юнит NN: покрытие источника, контракт данных, сохранность предыдущих юнитов."""
import hashlib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 62
# Сколько пунктов в каждом упражнении страницы-источника: NN.1, NN.2, …
SOURCE_ITEMS = [12, 9, 5]
# Пункты источника, которые не стали вопросами: причина из реестра в отчёте юнита.
NOT_TRANSFERRED = {"62.1.1": "Заполненный образец источника сохранён в preview упражнения 62.1.", "62.2.1": "Заполненный образец источника сохранён в preview упражнения 62.4.", "62.3.1": "Заполненный образец источника сохранён в preview упражнения 62.5."}
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
    covered = {re.sub(r"[a-z]$", "", r) for r in used}
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


def test_contrast_keys():
    assert by_ref("62.1.2")["answers"] == ["he ido"]
    assert by_ref("62.1.4")["answers"] == ["Estuvimos"]
    assert by_ref("62.1.3")["answers"] == ["nació"]
    assert by_ref("62.1.10")["answers"] == ["he visto"]
    assert by_ref("62.2.4")["answers"] == ["ha habido"]
    assert by_ref("62.2.5")["answers"] == ["hubo"]


def test_both_tenses_accepted_where_both_are_normative():
    assert by_ref("62.2.2")["answers"] == ["ha tenido", "tuvo"]
    assert by_ref("62.2.9b")["answers"] == ["pasamos", "hemos pasado"]


def test_dialogue_gaps_and_builds():
    for ref, answer in [("62.2.6", "Has visto vi"), ("62.2.7", "Habéis estado estuvimos"), ("62.2.8", "Has sacado compré"), ("62.2.9a", "han hecho estuvimos")]:
        q = by_ref(ref)
        assert q["answers"] == [answer] and len(q["gapParts"]) == 3
        assert sum(q["gapWordCounts"]) == len(answer.split())
    for ref in ("62.3.2a", "62.3.3a", "62.3.4a", "62.3.5a"):
        q = by_ref(ref)
        assert q["interaction"] == "build" and q["answers"][0].split() and set(q["answers"][0].split()) < set(q["tiles"])
        assert len(q["tiles"]) - len(q["answers"][0].split()) == 2


def test_typed_groups_are_strict_and_varied():
    u = unit()
    assert all(g.get("accentPolicy") == "strict" for g in u["exercises"] if g.get("inlineAnswer"))
    qs = [q for g in u["exercises"] for q in g["questions"]]
    assert len(qs) == 36
    assert len({q["learningAction"] for q in qs}) >= 4
