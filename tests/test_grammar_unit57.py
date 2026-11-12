"""Юнит 57: реестр источника, нормативные альтернативы и неизменность прежних уроков."""
import hashlib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 57
SOURCE_ITEMS = [3, 8, 7, 8]
NOT_TRANSFERRED = {
    "57.2.1": "Заполненный образец «no llueve» находится на вступительном экране 57.2.",
    "57.4.1": "Заполненные «vas / voy» находятся на вступительном экране 57.4.",
}


def unit():
    return next(u for u in load_grammar() if u["number"] == NUMBER)


def source_questions():
    return [q for g in unit()["exercises"] for q in g["questions"] if q.get("sourceRef") != "extra"]


def by_ref(ref):
    return next(q for q in source_questions() if q["sourceRef"] == ref)


def test_previous_grammar_units_untouched():
    baseline = json.loads(Path("tests/data/grammar_before_unit57.json").read_text(encoding="utf-8"))
    paths = sorted(p for p in GRAMMAR.glob("[0-9]*.json") if int(p.name[:3]) < NUMBER)
    assert len(paths) == len(baseline) == 54
    for path in paths:
        assert hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == baseline[path.name], path.name


def test_complete_book_coverage():
    refs = [q["sourceRef"] for q in source_questions()]
    assert len(refs) == len(set(refs))
    expected = {f"57.{gi}.{i}" for gi, n in enumerate(SOURCE_ITEMS, 1) for i in range(1, n+1)}
    covered = {re.sub(r"[a-z]$", "", ref) for ref in refs}
    assert covered.isdisjoint(NOT_TRANSFERRED)
    assert covered | set(NOT_TRANSFERRED) == expected
    assert len(covered) == 24
    assert all(len(reason) >= 15 for reason in NOT_TRANSFERRED.values())


def test_unit_contract_and_order():
    u = unit()
    assert u["id"] == "057_hago_estoy_haciendo"
    assert u["learningOrder"] == [
        "section:0", "exercise:57.1", "section:1", "exercise:57.2",
        "section:2", "section:3", "exercise:57.3", "exercise:57.4", "summary"
    ]
    assert len(u["sections"]) == 4
    assert [len(g["questions"]) for g in u["exercises"]] == [10, 11, 11, 10]
    for s in u["sections"]:
        assert s["title"] and s["paragraphs"] and s["presentation"] in {"comparison", "examples", "paradigm"}
        assert s["check"]["title"] == "Мини-проверка"
        assert s["check"]["instruction"]
        assert len(s["check"]["questions"]) == 3
        assert all(q.get("options") and set(q["answers"]) <= set(q["options"]) for q in s["check"]["questions"])
    for g in u["exercises"]:
        assert g["theorySections"] and g["accentPolicy"] == "strict"
        assert g["title"].startswith(g["id"] + " · ")
        for q in g["questions"]:
            assert q["context"] and q["explain"] and q["sourceRef"] and q["learningAction"]
            for field in ("prompt","context","explain","translation"):
                assert "`" not in q.get(field, "") and "**" not in q.get(field, ""), (g["id"],field)
            if q.get("options"):
                assert set(q["answers"]) <= set(q["options"])
            if not q.get("options") and not q.get("tiles"):
                assert q["inputChars"] == ["á","é","í","ó","ú","ü","ñ"]
                fmt = q.get("inputFormat",g.get("inputFormat"))
                assert fmt and fmt["instruction"] and fmt["placeholder"]
            if q.get("gapParts"):
                assert len(q["gapParts"]) == len(q["gapWordCounts"]) + 1
                assert sum(q["gapWordCounts"]) == len(q["answers"][0].split())


def test_situations_have_generated_art():
    raw = json.loads((GRAMMAR / "057_hago_estoy_haciendo.json").read_text(encoding="utf-8"))
    questions = raw["exercises"][0]["questions"]
    images = [q for q in questions if q.get("image")]
    assert len(images) == 3
    assert {q["sourceRef"] for q in images} == {"57.1.1a","57.1.2a","57.1.3b"}
    for q in images:
        assert q["imageAlt"] and q["image"].startswith("art/057/")
        path = GRAMMAR / q["image"]
        assert path.exists() and path.suffix == ".webp" and path.stat().st_size > 5000
    assert (GRAMMAR / "art/057/prompts.json").exists()


def test_grammar_meaning_and_alternatives():
    u = unit()
    text = " ".join(" ".join(s["paragraphs"]) for s in u["sections"])
    for phrase in ("conocer","comprender","entender","querer","necesitar","amar","preferir","odiar","parecer","tener","llevar","ir","venir","ver","oír"):
        assert phrase in text, phrase
    assert by_ref("57.1.1b")["gapWordCounts"] == [2,2]
    assert by_ref("57.4.6")["gapWordCounts"] == [1,1]
    assert by_ref("57.4.8")["gapWordCounts"] == [1,1,1]
    assert set(by_ref("57.4.4")["answers"]) == {"ves","estás viendo"}
    assert set(by_ref("57.3.1")["answers"]) == {"Оба возможны; нейтральнее vais."}
    assert "не абсолютный" in " ".join(u["sections"][2]["paragraphs"]).lower()
    assert any("¿Qué haces?" in p for p in u["sections"][3]["paragraphs"])


def test_report_exists():
    assert Path("docs/grammar_units/57.md").is_file()
