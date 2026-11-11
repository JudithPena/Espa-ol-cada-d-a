"""Fable stage 9: semantic practice and answer fairness in unit 14 (gentilicios)."""

from collections import Counter

from espanol.grammar import load_grammar
from espanol.grammar_quality import pedagogical_unit


def unit14():
    return next(unit for unit in load_grammar() if unit["number"] == 14)


def groups(unit):
    return [section["check"] for section in unit["sections"]] + unit["exercises"]


def test_unit14_keeps_routes_ids_and_invalidates_old_attempts():
    unit = unit14()
    assert unit["id"] == "014_gentilicios"
    assert unit["revision"] == 2
    assert [g["id"] for g in groups(unit)] == [
        "check-a", "check-b", "check-c", "14.1", "14.2", "14.3"
    ]
    assert [g["revision"] for g in groups(unit)] == [2, 2, 2, 3, 2, 2]
    assert [g["theorySections"] for g in unit["exercises"]] == [[0], [1], [2]]
    assert unit["learningOrder"] == [
        "section:0", "exercise:14.1", "section:1", "exercise:14.2",
        "section:2", "exercise:14.3", "summary"
    ]
    assert [len(section["check"]["questions"]) for section in unit["sections"]] == [3, 3, 3]
    assert [len(exercise["questions"]) for exercise in unit["exercises"]] == [15, 10, 11]
    assert sum(len(g["questions"]) for g in groups(unit)) == 45
    assert all(section["illustration"]["image"] for section in unit["sections"])


def test_unit14_every_question_has_a_clear_scorable_answer():
    for group in groups(unit14()):
        assert group["instruction"]
        assert len({q["prompt"] for q in group["questions"]}) == len(group["questions"])
        for q in group["questions"]:
            assert q["context"] and len(q["explain"]) >= 70, (group["id"], q["prompt"])
            assert q["answers"]
            if q.get("options"):
                assert q["interaction"] in {"choice", "gap-choice"}
                assert len(q["options"]) == len(set(q["options"]))
                assert set(q["answers"]) <= set(q["options"])
            else:
                assert q["interaction"] == "input"
                fmt = q.get("inputFormat", group.get("inputFormat"))
                assert fmt and fmt["instruction"] and fmt["placeholder"]


def test_first_group_practises_five_models_and_spelling():
    ex = unit14()["exercises"][0]
    assert Counter(q["interaction"] for q in ex["questions"]) == {
        "input": 10, "gap-choice": 2, "choice": 3
    }
    assert any(q["answers"] == ["chilena"] for q in ex["questions"])
    assert any(q["answers"] == ["japonesa"] for q in ex["questions"])
    assert any(q["answers"] == ["alemana"] for q in ex["questions"])
    assert any(q["answers"] == ["costarricenses"] for q in ex["questions"])
    assert any(q["answers"] == ["vietnamitas"] for q in ex["questions"])
    assert any(q["answers"] == ["nicaragüenses"] for q in ex["questions"])
    assert any(q["answers"] == ["japonés"] and q["interaction"] == "input"
               for q in ex["questions"])
    assert any("vietnamito" in q["prompt"] for q in ex["questions"])
    assert any("Chile" in q["answers"][0] and "chileno" in q["answers"][0]
               for q in ex["questions"])
    both = [q for q in ex["questions"] if "iraníes" in q["answers"]]
    assert len(both) == 1 and set(both[0]["answers"]) == {"iraníes", "iranís"}
    assert both[0]["interaction"] == "input"
    # No copying an already-given identical answer into a free-text field.
    for q in ex["questions"]:
        if q["interaction"] == "input" and q.get("clues"):
            assert all(a != clue[0] for a in q["answers"] for clue in q["clues"])


def test_second_group_differentiates_ser_and_noun_articles():
    ex = unit14()["exercises"][1]
    assert Counter(q["interaction"] for q in ex["questions"]) == {
        "input": 5, "gap-choice": 3, "choice": 2
    }
    assert any(q["answers"] == ["una"] and "amiga" in q["prompt"]
               for q in ex["questions"])
    assert any(q["answers"] == ["una amiga chilena"] and q["interaction"] == "input"
               for q in ex["questions"])
    assert any(q["answers"] == ["Soy chilena."] for q in ex["questions"])
    assert any(q["answers"] == ["Soy de Chile."] and "ser + de" in q["prompt"]
               for q in ex["questions"])
    assert any(q["answers"] == ["mexicanos"] and "Pablo y Ana" in q["prompt"]
               for q in ex["questions"])
    assert "существительному" in " ".join(unit14()["sections"][1]["paragraphs"])


def test_third_group_practises_spanish_noun_gender_and_both_marroqui_plurals():
    ex = unit14()["exercises"][2]
    assert Counter(q["interaction"] for q in ex["questions"]) == {
        "input": 7, "gap-choice": 1, "choice": 3
    }
    both = [q for q in ex["questions"] if "marroquíes" in q["answers"]]
    assert len(both) == 1 and set(both[0]["answers"]) == {"marroquíes", "marroquís"}
    assert both[0]["interaction"] == "input"
    assert any(q["answers"] == ["francesas"] and "ciudades" in q["prompt"]
               for q in ex["questions"])
    assert any(q["answers"] == ["dos ciudades portuguesas"]
               for q in ex["questions"])
    assert any(q["answers"] == ["chilena"] and "amiga" in q["prompt"]
               for q in ex["questions"])
    assert any(q["answers"] == ["estadounidenses"]
               for q in ex["questions"])
    assert any(q["answers"] == ["alemanes"]
               for q in ex["questions"])


def test_linter_does_not_find_structural_or_methodical_regressions():
    findings = pedagogical_unit(unit14(), "014_gentilicios.json")
    blockers = {
        "SHORT_CHECK", "DUPLICATE_PROMPTS", "LONG_HOMOGENEOUS",
        "LONG_MODE_RUN", "GENERIC_EXPLANATION", "INPUT_WORDING_FOR_CHOICES",
        "UNIT_FORMAT_DIVERSITY", "BUILD_WITHOUT_DISTRACTORS",
    }
    assert not [f for f in findings if f.rule in blockers], [
        (f.rule, f.group, f.question) for f in findings
    ]
