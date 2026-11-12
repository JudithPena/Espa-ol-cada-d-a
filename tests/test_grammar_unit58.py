"""Юнит 58: полнота стр. 124–125, форма indefinido, сохранность предыдущих 55 юнитов."""
import hashlib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 58
SOURCE_ITEMS = (8, 8, 13, 8)
NOT_TRANSFERRED = {
    "58.1.1": "Заполненный пример se casaron сохранён в preview 58.1.",
    "58.2.1": "Заполненный пример conociste сохранён в preview 58.2.",
    "58.3.1": "Заполненный пример despertó сохранён в preview 58.3.",
    "58.4.1": "Заполненный пример nació сохранён в preview 58.4.",
}


def unit():
    return next(u for u in load_grammar() if u["number"] == NUMBER)


def questions():
    return [q for g in unit()["exercises"] for q in g["questions"]]


def by_ref(ref):
    return next(q for q in questions() if q["sourceRef"] == ref)


def test_previous_55_grammar_units_are_identical():
    baseline = json.loads(Path("tests/data/grammar_before_unit58.json").read_text(encoding="utf-8"))
    files = sorted(p for p in GRAMMAR.glob("[0-9]*.json") if int(p.name[:3]) < NUMBER)
    assert len(files) == len(baseline) == 55
    for file in files:
        digest = hashlib.sha256(file.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert digest == baseline[file.name], file.name


def test_every_source_item_accounted_for():
    refs = [q["sourceRef"] for q in questions() if q["sourceRef"] != "extra"]
    assert len(refs) == len(set(refs)) == 36
    expected = {f"58.{g}.{i}" for g, count in enumerate(SOURCE_ITEMS, 1) for i in range(1, count + 1)}
    covered = {re.sub(r"[a-z]$", "", ref) for ref in refs}
    assert len(expected) == 37
    assert len(covered) == 33
    assert not covered.intersection(NOT_TRANSFERRED)
    assert covered | set(NOT_TRANSFERRED) == expected
    assert sum(q["sourceRef"] == "extra" for q in questions()) == 11


def test_learning_route_and_unit_structure():
    u = unit()
    assert u["id"] == "058_trabaje_comi_vivi"
    assert u["number"] == 58 and u["level"] == "A2"
    assert u["learningOrder"] == [
        "section:0", "exercise:58.1", "section:1", "exercise:58.2",
        "section:2", "exercise:58.3", "section:3", "exercise:58.4", "summary"
    ]
    assert len(u["sections"]) == 4
    assert [len(g["questions"]) for g in u["exercises"]] == [13, 10, 14, 10]
    for sec in u["sections"]:
        assert sec["title"] and sec["paragraphs"] and sec["presentation"] in {"paradigm", "examples", "comparison"}
        check = sec["check"]
        assert check["title"] == "Мини-проверка" and len(check["questions"]) == 3
        assert all(q["options"] and set(q["answers"]) <= set(q["options"]) for q in check["questions"])
    for ex in u["exercises"]:
        assert ex["accentPolicy"] == "strict" and ex["theorySections"] and ex["inlineAnswer"]
        assert ex["title"].startswith(ex["id"] + " · ")
        assert ex["preview"]["answer"]
        for q in ex["questions"]:
            assert q["context"] and q["prompt"] and q["explain"] and q["learningAction"]
            assert q["sourceRef"]
            if not q.get("options") and not q.get("tiles"):
                assert q["inputChars"] == ["á", "é", "í", "ó", "ú", "ü", "ñ"]
            if q.get("options"):
                assert set(q["answers"]) <= set(q["options"])
            if q.get("gapParts"):
                assert len(q["gapParts"]) == len(q["gapWordCounts"]) + 1
                assert sum(q["gapWordCounts"]) == len(q["answers"][0].split())
            for f in ("prompt", "context", "explain"):
                assert not any(m in q[f] for m in ("**", "`")), (ex["id"], f)


def test_complete_three_regular_paradigms_and_both_pronoun_rows():
    u = unit()
    table = u["sections"][0]["table"]
    assert table["heads"] == ["Кто", "trabajar (-ar)", "comer (-er)", "vivir (-ir)"]
    assert len(table["rows"]) == 8 and table["compactForms"] is True
    rows = {r[0]: r[1:] for r in table["rows"]}
    assert rows["yo"] == ["trabajé", "comí", "viví"]
    assert rows["tú"] == ["trabajaste", "comiste", "viviste"]
    assert rows["nosotros / -as"] == ["trabajamos", "comimos", "vivimos"]
    assert rows["vosotros / -as"] == ["trabajasteis", "comisteis", "vivisteis"]
    assert rows["ellos / -as"] == ["trabajaron", "comieron", "vivieron"]


def test_orthography_and_special_short_forms():
    u = unit()
    two = " ".join(u["sections"][1]["paragraphs"])
    for word in ("saqué", "empecé", "llegué", "di", "dio", "vi", "vio"):
        assert word in two
    assert by_ref("58.1.3")["answers"] == ["vimos"]
    assert by_ref("58.2.2")["answers"] == ["disteis"]
    assert by_ref("58.3.8")["answers"] == ["di"]
    assert by_ref("58.3.11")["answers"] == ["apagué"]
    assert "dí" not in by_ref("58.3.8")["answers"]
    assert "vió" not in by_ref("58.3.6")["answers"]


def test_story_order_and_reflexive_forms():
    qs = [q for q in unit()["exercises"][2]["questions"] if q["sourceRef"] != "extra"]
    assert [q["sourceRef"] for q in qs] == [f"58.3.{i}" for i in range(2, 14)]
    assert [q["answers"][0] for q in qs] == [
        "Me levanté", "encendí", "me acerqué", "vi", "vio", "llamó",
        "di", "se alejó", "regresé", "apagué", "me acosté", "volví"
    ]
    assert by_ref("58.1.6")["answers"] == ["os conocisteis nos conocimos"]


def test_biography_reflexives_and_source_models():
    u = unit()
    source = [q for q in u["exercises"][3]["questions"] if q["sourceRef"] != "extra"]
    assert [q["sourceRef"] for q in source] == [f"58.4.{i}" for i in range(2, 9)]
    assert [q["answers"][0] for q in source] == [
        "se trasladó", "se casó", "nació", "se refugió",
        "vivió", "escribió", "regresó"
    ]
    assert [g["preview"]["answer"] for g in u["exercises"]] == [
        "se casaron", "conociste", "despertó", "nació"
    ]
    assert Path("docs/grammar_units/58.md").is_file()
