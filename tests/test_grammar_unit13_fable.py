"""Fable stage 6: adjective agreement, gender models, apocope and progress stability."""
from collections import Counter

from espanol.grammar import load_grammar
from espanol.grammar_quality import pedagogical_unit


def unit13():
    return next(u for u in load_grammar() if u["number"] == 13)


def groups(u):
    return [s["check"] for s in u["sections"]] + u["exercises"]


def test_unit13_preserves_ids_routes_and_revisions():
    u = unit13()
    assert u["id"] == "013_adjetivos" and u["revision"] == 2
    assert [g["id"] for g in groups(u)] == [
        "check-a", "check-b", "check-c", "13.1", "13.2", "13.3"
    ]
    assert all(g["revision"] == 2 for g in groups(u))
    assert u["learningOrder"] == [
        "section:0", "exercise:13.1", "section:1", "exercise:13.2",
        "section:2", "exercise:13.3", "summary"
    ]
    assert [g["theorySections"] for g in u["exercises"]] == [[0], [1], [2]]
    assert [len(g["questions"]) for g in u["exercises"]] == [12, 13, 14]
    assert [len(s["check"]["questions"]) for s in u["sections"]] == [3, 3, 3]
    assert sum(len(g["questions"]) for g in groups(u)) == 48


def test_unit13_every_question_scorable_clear_and_explained():
    u = unit13()
    for group in groups(u):
        for q in group["questions"]:
            assert q["context"] and len(q["explain"]) >= 70, (group["id"], q["prompt"])
            if q.get("options"):
                assert len(q["options"]) == len(set(q["options"]))
                assert set(q["answers"]) <= set(q["options"])
                assert q["interaction"] in {"choice", "gap-choice"}
            elif q.get("tiles"):
                assert q["interaction"] == "build"
                assert len(q["tiles"]) > len(q["answers"][0].split())
                assert set(q["answers"][0].split()) <= set(q["tiles"])
                assert all(q["inputFormat"].get(k) for k in ("instruction", "placeholder"))
            else:
                assert q["interaction"] == "input"
                assert all(q["inputFormat"].get(k) for k in ("instruction", "placeholder"))
    # Single unchanged adjective is intentional: el mapa (masculine ending -a).
    copied = [q for q in u["exercises"][0]["questions"]
              if q.get("clues") and q["answers"][0] == q["clues"][0][0]]
    assert len(copied) == 1 and copied[0]["prompt"] == "El mapa es ___."


def test_unit13_models_number_and_accents_are_actually_practised():
    u = unit13()
    qs = u["exercises"][1]["questions"]
    for part, answer in [
        ("unas chicas ___", "alegres"),
        ("Mis amigos son ___", "felices"),
        ("dos faldas ___", "marrones"),
        ("dos chicos ___", "jóvenes"),
        ("Marta es muy ___", "charlatana"),
        ("Sus hermanas son ___", "trabajadoras"),
        ("Concha y Rodrigo", "trabajadores"),
    ]:
        match = [q for q in qs if part in q["prompt"]]
        assert len(match) == 1 and match[0]["answers"] == [answer], part
    assert any("почему" in q["prompt"].lower() and "inteligentes" in q["prompt"]
               for q in qs)
    text = " ".join(" ".join(s["paragraphs"]) for s in u["sections"])
    for example in ("joven → jóvenes", "feliz → felices", "marrón → marrones",
                    "charlatán / charlatana", "un chico alegre", "una chica alegre"):
        assert example in text


def test_unit13_buen_mal_and_full_forms_have_sufficient_contrast_and_build_distractors():
    u = unit13()
    g = u["exercises"][2]
    assert "buen" in g["title"].lower() and "mal" in g["title"].lower()
    answers = [q["answers"][0] for q in g["questions"]]
    assert "buen" in answers and "mal" in answers and "bueno" in answers
    assert "buena" in answers and "mala" in answers and "malo" in answers
    assert len([q for q in g["questions"] if q.get("tiles")]) == 2
    assert any("обе" in q["explain"].lower() and "profesor bueno" in q["prompt"]
               for q in g["questions"])
    assert all("ojos azules" not in q["prompt"] for q in g["questions"])
    assert all(len(q["tiles"]) >= 5 for q in g["questions"] if q.get("tiles"))


def test_unit13_varied_operations_and_pedagogical_lint():
    u = unit13()
    assert [Counter(q["interaction"] for q in g["questions"]) for g in u["exercises"]] == [
        Counter({"input": 7, "gap-choice": 3, "choice": 2}),
        Counter({"input": 6, "gap-choice": 3, "choice": 4}),
        Counter({"input": 4, "gap-choice": 6, "choice": 2, "build": 2}),
    ]
    findings = pedagogical_unit(u, "013_adjetivos.json")
    critical = {"SHORT_CHECK", "DUPLICATE_PROMPTS", "LONG_HOMOGENEOUS",
                "GENERIC_EXPLANATION", "INPUT_WORDING_FOR_CHOICES",
                "UNIT_FORMAT_DIVERSITY", "BUILD_WITHOUT_DISTRACTORS"}
    assert not [f for f in findings if f.rule in critical], [
        (f.rule, f.group, f.question) for f in findings
    ]
