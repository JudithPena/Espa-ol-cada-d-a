"""Fable stage 4: unit 7 pedagogical, normative and progress regressions."""
from collections import Counter

from espanol.grammar import load_grammar
from espanol.grammar_quality import pedagogical_unit


def unit7():
    return next(unit for unit in load_grammar() if unit["number"] == 7)


def all_groups(unit):
    return [section["check"] for section in unit["sections"]] + unit["exercises"]


def test_unit7_keeps_existing_routes_and_progress_ids_but_revisions_restart_stale_attempts():
    unit = unit7()
    assert unit["id"] == "007_un_perro_el_perro"
    assert unit["revision"] == 2
    assert len(unit["sections"]) == 3
    assert [group["id"] for group in all_groups(unit)] == [
        "check-a", "check-b", "check-c", "7.1", "7.2", "7.3"
    ]
    assert all(group["revision"] == 2 for group in all_groups(unit))
    assert unit["learningOrder"] == [
        "section:0", "exercise:7.1", "section:1", "exercise:7.2",
        "section:2", "exercise:7.3", "summary"
    ]


def test_unit7_is_concise_and_requires_independent_article_production():
    unit = unit7()
    assert [len(g["questions"]) for g in unit["exercises"]] == [12, 12, 12]
    assert [len(s["check"]["questions"]) for s in unit["sections"]] == [3, 3, 3]
    assert sum(bool(q.get("options")) for g in unit["exercises"] for q in g["questions"]) == 17
    assert sum(not q.get("options") for g in unit["exercises"] for q in g["questions"]) == 19
    assert all(
        g["instruction"] and g["theorySections"] == [i]
        for i, g in enumerate(unit["exercises"])
    )
    assert all(section["check"]["instruction"] for section in unit["sections"])
    for group in all_groups(unit):
        for q in group["questions"]:
            assert (q["prompt"].count("___") == 1 or
                    q["interaction"] == "choice" and "___" not in q["prompt"]), (group["id"], q["prompt"])
            assert q["explain"] and len(q["explain"]) > 35
            assert q["context"]
            if q.get("options"):
                assert set(q["answers"]) <= set(q["options"])
                assert len(q["options"]) == len(set(q["options"]))
            else:
                assert q["interaction"] == "article-input"
                assert "артикль" in q["inputFormat"]["instruction"].lower()


def test_unit7_no_article_is_a_real_answer_and_plural_alternatives_are_accepted():
    unit = unit7()
    groups = all_groups(unit)
    assert not any(
        "Без артикля" in q.get("options", [])
        for g in unit["exercises"][:2] for q in g["questions"]
    )
    no_article = [
        q for g in groups for q in g["questions"]
        if "Без артикля" in q["answers"]
    ]
    assert len(no_article) == 5
    assert unit["exercises"][2]["allowNoArticle"] is True
    plurals = unit["exercises"][2]["questions"]
    peras = next(q for q in plurals if "Compro ___ peras" in q["prompt"])
    manzanas = next(q for q in plurals if "Compro ___ manzanas" in q["prompt"])
    bombones = next(q for q in plurals if "Tengo ___ bombones" in q["prompt"])
    for question, article in [(peras, "unas"), (manzanas, "unas"), (bombones, "unos")]:
        assert set(question["answers"]) == {article, "Без артикля"}
        assert article in question["explain"].lower()
        assert ("без артикля" in question["explain"].lower()
                or "Compro manzanas" in question["explain"])


def test_unit7_meaningful_contrasts_and_no_long_guessing_run():
    unit = unit7()
    assert {"un", "una", "el", "la"} <= {
        ans for g in unit["exercises"][:2] for q in g["questions"] for ans in q["answers"]
    }
    assert {"los", "las", "unos", "unas", "Без артикля"} <= {
        ans for q in unit["exercises"][2]["questions"] for ans in q["answers"]
    }
    for group in all_groups(unit):
        if group["id"].startswith("check"):
            continue
        count = Counter("choice" if q.get("options") else "input" for q in group["questions"])
        assert count["choice"] > 0 and count["input"] > 0
    findings = pedagogical_unit(unit, "007_un_perro_el_perro.json")
    assert not [f for f in findings if f.rule in {
        "LONG_HOMOGENEOUS", "LONG_MODE_RUN", "NEVER_CORRECT_OPTION",
    }]
