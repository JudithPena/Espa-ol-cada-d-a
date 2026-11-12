"""Юнит 56: полнота исходника, справедливая проверка и неизменность старых юнитов."""
import hashlib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 56
SOURCE_ITEMS = [8, 11, 6]
NOT_TRANSFERRED = {
    "56.1.1": "Заполненный образец Estoy escribiendo una carta перенесён на вступительный экран 56.1",
    "56.2.1": "Заполненный образец Están pasando unos días en Potosí перенесён на вступительный экран 56.2",
    "56.3.1": "Заполненный образец Estoy estudiando español приведён как образец построения формы в первом блоке теории",
    "56.3.2": "Заполненный образец No me estoy duchando перенесён на вступительный экран 56.4",
}


def unit():
    return next(u for u in load_grammar() if u["number"] == NUMBER)


def questions():
    return [q for g in unit()["exercises"] for q in g["questions"]]


def by_ref(ref):
    return next(q for q in questions() if q["sourceRef"] == ref)


def test_existing_units_remain_byte_identical():
    baseline = json.loads(Path("tests/data/grammar_before_unit56.json").read_text(encoding="utf-8"))
    paths = sorted(p for p in GRAMMAR.glob("[0-9]*.json") if int(p.name[:3]) < NUMBER)
    assert len(paths) == len(baseline) == 53
    for path in paths:
        digest = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert digest == baseline[path.name], path.name


def test_every_book_item_is_accounted_for_once():
    refs = [q["sourceRef"] for q in questions() if q["sourceRef"] != "extra"]
    assert len(refs) == len(set(refs))
    expected = {f"{NUMBER}.{g}.{i}" for g, n in enumerate(SOURCE_ITEMS, 1) for i in range(1, n + 1)}
    covered = {re.sub(r"[a-z]$", "", r) for r in refs}
    assert covered.isdisjoint(NOT_TRANSFERRED)
    assert covered | set(NOT_TRANSFERRED) == expected
    assert len(covered) == 21 and len(NOT_TRANSFERRED) == 4


def test_format_and_route():
    u = unit()
    assert u["id"] == "056_estoy_viendo"
    assert u["learningOrder"] == [
        "section:0", "exercise:56.1", "section:1", "exercise:56.2",
        "section:2", "exercise:56.3", "section:3", "exercise:56.4", "summary"
    ]
    assert [len(g["questions"]) for g in u["exercises"]] == [10, 10, 6, 8]
    assert all(g["accentPolicy"] == "strict" for g in u["exercises"])
    assert all(g["theorySections"] for g in u["exercises"])
    assert all(s["presentation"] in {"paradigm", "comparison", "examples"} for s in u["sections"])
    for section in u["sections"]:
        check = section["check"]
        assert check["title"] == "Мини-проверка"
        assert len(check["questions"]) == 3
        assert all(q.get("options") and set(q["answers"]) <= set(q["options"]) for q in check["questions"])
    for group in u["exercises"]:
        assert group["title"].startswith(group["id"] + " · ")
        assert group["inputFormat"]["instruction"] and group["inputFormat"]["placeholder"]
        for q in group["questions"]:
            assert q["context"] and q["explain"] and q["learningAction"]
            assert "sourceRef" in q
            if not q.get("options") and not q.get("tiles"):
                assert q["inputChars"] == ["á", "é", "í", "ó", "ú", "ü", "ñ"]
            if q.get("gapParts"):
                assert len(q["gapParts"]) == len(q["gapWordCounts"]) + 1
                assert sum(q["gapWordCounts"]) == len(q["answers"][0].split())


def test_book_pictures_are_adapted_to_text_and_input():
    assert by_ref("56.1.2")["answers"] == ["Están jugando"]
    assert by_ref("56.1.3")["answers"] == ["está nevando"]
    assert by_ref("56.1.4")["gapWordCounts"] == [2, 2]
    assert by_ref("56.1.6")["answers"] == ["están llorando"]
    assert by_ref("56.2.3")["answers"] == ["están discutiendo"]
    assert by_ref("56.2.6")["answers"] == ["estáis pensando"]
    assert by_ref("56.3.4")["answers"] == ["está lloviendo"]


def test_reflexive_pronoun_positions_and_accents():
    g = unit()["exercises"][3]
    assert set(by_ref("56.2.10")["answers"]) == {"nos estamos acostando", "estamos acostándonos"}
    assert {"me estoy duchando", "estoy duchándome"} <= set(g["questions"][5]["answers"])
    assert {"se está vistiendo", "está vistiéndose"} <= set(g["questions"][6]["answers"])
    assert g["questions"][7]["tiles"] == ["se", "vistiendo", "están", "estáis", "me"]
    assert "está" in unit()["sections"][0]["table"]["rows"][2][1]
    assert "estáis" in unit()["sections"][0]["table"]["rows"][4][1]


def test_report_exists():
    assert Path("docs/grammar_units/56.md").is_file()
