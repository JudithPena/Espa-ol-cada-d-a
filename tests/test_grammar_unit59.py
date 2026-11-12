"""Unit 59: source 59.1-59.3, irregular paradigms, accepted forms, old-unit immutability."""
import hashlib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 59
SOURCE_ITEMS = (12, 9, 2)
PREVIEWS = {
    "59.1.1": "A filled Alba vino example in the 59.1c intro.",
    "59.2.1": "The prefilled Cuba example in 59.2 has historically corrected year 1902.",
    "59.3.1": "The filled first dialogue line hiciste is in the 59.3 intro, other lines are independent questions.",
}


def raw():
    return json.loads((GRAMMAR / "059_durmio_leyo_hizo.json").read_text(encoding="utf-8"))


def unit():
    return next(u for u in load_grammar() if u["number"] == NUMBER)


def questions():
    return [q for group in unit()["exercises"] for q in group["questions"]]


def by_ref(ref):
    return next(q for q in questions() if q["sourceRef"] == ref)


def test_all_58_prior_units_unchanged():
    baseline = json.loads(Path("tests/data/grammar_before_unit59.json").read_text(encoding="utf-8"))
    old = sorted(p for p in GRAMMAR.glob("[0-9]*.json") if int(p.name[:3]) < NUMBER)
    assert len(old) == len(baseline) == 58
    for path in old:
        assert hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == baseline[path.name], path.name


def test_all_book_exercises_accounted_for():
    refs = [q["sourceRef"] for q in questions() if q["sourceRef"] != "extra"]
    assert len(refs) == len(set(refs)) == 27
    expected = {f"59.{group}.{i}" for group, n in enumerate(SOURCE_ITEMS, 1) for i in range(1, n+1)}
    covered = {re.sub(r"[a-z]$", "", ref) for ref in refs}
    assert len(expected) == 23
    assert covered | set(PREVIEWS) == expected
    assert len(covered) == 21
    assert covered.intersection(PREVIEWS) == {"59.3.1"}
    assert len([q for q in questions() if q["sourceRef"] == "extra"]) == 24
    assert [g["preview"]["answer"] for g in unit()["exercises"]] == [
        "pedí", "leyó", "vino", "traduje", "se independizó", "hiciste"
    ]


def test_theory_route_and_contract():
    u = unit()
    assert u["id"] == "059_durmio_leyo_hizo" and u["level"] == "A2"
    assert u["learningOrder"] == [
        "section:0", "exercise:59.1a", "section:1", "exercise:59.1b",
        "section:2", "exercise:59.1c", "section:3", "exercise:59.1d",
        "section:4", "exercise:59.2", "exercise:59.3", "summary"
    ]
    assert len(u["sections"]) == 5
    assert [len(g["questions"]) for g in u["exercises"]] == [8, 7, 11, 5, 10, 10]
    for section in u["sections"]:
        assert section["title"] and section["paragraphs"]
        assert section["presentation"] in {"paradigm","comparison","examples"}
        assert len(section["check"]["questions"]) == 3
        assert all(q.get("options") and set(q["answers"]) <= set(q["options"]) for q in section["check"]["questions"])
    for group in u["exercises"]:
        assert group["accentPolicy"] == "strict"
        assert group["preview"]["answer"] and group["theorySections"]
        assert group["title"].startswith(group["id"]+" · ")
        for q in group["questions"]:
            assert q["prompt"] and q["context"] and q["explain"] and q["sourceRef"] and q["learningAction"]
            for field in ("prompt","context","explain"):
                assert not any(marker in q[field] for marker in ("**", "`"))
            if q.get("options"):
                assert set(q["answers"]) <= set(q["options"])
            if not q.get("options") and not q.get("tiles"):
                assert q["inputChars"] == ["á","é","í","ó","ú","ü","ñ"]
            if q.get("gapParts"):
                assert len(q["gapParts"]) == len(q["gapWordCounts"])+1
                assert sum(q["gapWordCounts"]) == len(q["answers"][0].split())
            if q.get("tiles"):
                words = q["answers"][0].split()
                for word in set(words):
                    assert words.count(word) <= q["tiles"].count(word)
    assert len(u["summary"]["rows"]) == 8


def test_ir_stem_change_is_third_person_only():
    table = unit()["sections"][0]["table"]
    rows = {r[0]: r[1:] for r in table["rows"]}
    assert rows["yo"] == ["pedí", "dormí"]
    assert rows["nosotros / -as"] == ["pedimos", "dormimos"]
    assert rows["él / ella"] == ["pidió", "durmió"]
    assert rows["ellos / -as"] == ["pidieron", "durmieron"]
    assert by_ref("59.1.8")["answers"] == ["murieron"]


def test_y_and_j_forms_and_impersonal_haber():
    vowel = unit()["sections"][1]["table"]
    forms = {r[0]:r[1:] for r in vowel["rows"]}
    assert forms["yo"] == ["leí", "construí", "oí"]
    assert forms["usted / él / ella"] == ["leyó", "construyó", "oyó"]
    assert forms["ustedes / ellos"] == ["leyeron", "construyeron", "oyeron"]
    assert by_ref("59.1.5")["answers"] == ["construyó"]
    assert by_ref("59.1.11")["answers"] == ["pasó hubo"]
    assert by_ref("59.1.12")["answers"] == ["condujo"]
    assert by_ref("59.2.5")["answers"] == ["trajeron"]
    all_theory = " ".join(" ".join(s["paragraphs"]) for s in unit()["sections"])
    for form in ("dijeron","trajeron","condujeron","hizo","hubo","fueron"):
        assert form in all_theory, form


def test_ser_ir_ambiguity_and_source_history_corrections():
    u = unit()
    table = u["sections"][4]["table"]
    assert [r[1] for r in table["rows"]] == ["fui","fuiste","fue","fuimos","fuisteis","fueron"]
    assert by_ref("59.2.4")["answers"] == ["construyeron"]
    assert "siglo XV" in by_ref("59.2.4")["prompt"]
    assert "siglos IX y X" in by_ref("59.2.7")["prompt"]
    assert "1902" in u["exercises"][4]["preview"]["source"]
    assert by_ref("59.3.1a")["answers"] == ["fui"]
    assert by_ref("59.3.1e")["answers"] == ["fue"]
    assert by_ref("59.3.2c")["answers"] == ["divirtió"]
    assert Path("docs/grammar_units/59.md").is_file()
