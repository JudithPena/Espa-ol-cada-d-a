"""Юнит 54: покрытие источника, контракт данных, сохранность предыдущих юнитов."""
import hashlib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 54
# Сколько пунктов в каждом упражнении страницы-источника: NN.1, NN.2, …
SOURCE_ITEMS = [8, 8, 10]
# Пункты источника, которые не стали вопросами: причина из реестра в отчёте юнита.
NOT_TRANSFERRED = {"54.1.1": "заполненный образец Raúl lava coches показан на вступительном экране 54.1",
                   "54.2.1": "заполненный образец Felipe se aburre показан на вступительном экране 54.2",
                   "54.3.1": "заполненный образец Me llamo Andrés показан на вступительном экране 54.4"}
PLAIN_TEXT = ("prompt", "context", "explain", "translation", "answerHint")


def unit():
    return next(u for u in load_grammar() if u["number"] == NUMBER)


def questions():
    return [q for g in unit()["exercises"] for q in g["questions"]]


def by_ref(ref):
    return next(q for q in questions() if q["sourceRef"] == ref)


def test_previous_units_are_untouched():
    before = json.loads(Path(f"tests/data/grammar_before_unit{NUMBER}.json").read_text(encoding="utf-8"))
    assert len(before) == len([p for p in GRAMMAR.glob("[0-9]*.json") if int(p.name[:3]) < NUMBER])
    for name, digest in before.items():
        data = (GRAMMAR / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == digest, name


def test_every_source_item_is_accounted_for():
    refs = [q["sourceRef"] for q in questions()]
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


def test_with_and_without_se_contrast_both_ways():
    u = unit()
    assert all(g["accentPolicy"] == "strict" for g in u["exercises"])
    answers = {q["sourceRef"]: q["answers"] for q in questions() if q["sourceRef"] != "extra"}
    assert answers["54.1.3"] == ["despierta"] and answers["54.1.8"] == ["me despierto"]
    assert answers["54.1.6"] == ["mancha"] and answers["54.1.2"] == ["me mancho"]
    assert answers["54.2.3"] == ["viste se viste"]
    assert answers["54.3.8"] == ["encuentro"] and answers["54.3.7"] == ["me encontré"]
    assert answers["54.3.4"] == ["Vamos"] and answers["54.3.6"] == ["nos vamos"]
    # Clues name both verbs: the form with or without se is the learner's decision.
    for q in questions():
        for es, _ru in q.get("clues", []):
            if "/" in es:
                plain, refl = [x.strip() for x in es.split("/")]
                assert refl == plain + "se", es


def test_ambiguous_book_items_are_disambiguated_by_context():
    assert "клиенток" in by_ref("54.2.5")["context"]
    assert "забывчивост" in by_ref("54.3.10")["context"]
    assert by_ref("54.3.6")["prompt"].endswith("y ___.")
    assert by_ref("54.3.7")["translation"]


def test_report_exists():
    assert Path(f"docs/grammar_units/{NUMBER:02d}.md").exists()
