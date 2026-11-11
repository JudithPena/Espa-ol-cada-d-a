"""Fable stage 5: unit-5 meaning-based article, progress and pedagogy regression."""
from collections import Counter

from espanol.grammar import load_grammar
from espanol.grammar_quality import pedagogical_unit


def unit5():
    return next(unit for unit in load_grammar() if unit["number"] == 5)


def groups(unit):
    return [s["check"] for s in unit["sections"]] + unit["exercises"]


def test_unit5_keeps_route_ids_and_revision_invalidates_old_attempts():
    u = unit5()
    assert u["id"] == "005_sin_articulo"
    assert u["revision"] == 3
    assert [g["id"] for g in groups(u)] == ["check-a", "check-b", "check-c", "5.1", "5.2", "5.3"]
    assert all(g["revision"] == 3 for g in groups(u))
    assert u["learningOrder"] == ["section:0", "section:1", "exercise:5.1",
                                  "exercise:5.2", "section:2", "exercise:5.3", "summary"]
    assert [len(g["questions"]) for g in u["exercises"]] == [9, 13, 13]
    assert [len(s["check"]["questions"]) for s in u["sections"]] == [3, 3, 3]


def test_unit5_theory_matches_sections_and_never_teaches_article_absolutes():
    u = unit5()
    assert [g["theorySections"] for g in u["exercises"]] == [[0, 1], [0, 1], [2]]
    text = " ".join(" ".join(s["paragraphs"]) for s in u["sections"])
    for example in ["Es profesora de español", "Son protestantes", "Son socialistas",
                    "Compro manzanas", "Compro unas manzanas", "Es cantante"]:
        assert example.lower() in text.lower()
    assert all(not any(t in q["prompt"].lower() for t in ["se ha hecho", " era ", " fue "])
               for g in groups(u) for q in g["questions"])


def test_unit5_practice_requires_article_reasoning_not_instructions_that_give_away_answer():
    u = unit5()
    assert sum(len(g["questions"]) for g in groups(u)) == 44
    for group in groups(u):
        for q in group["questions"]:
            assert q["context"] and q["explain"] and len(q["explain"]) >= 65
            if q.get("options"):
                assert len(set(q["options"])) == len(q["options"])
                assert set(q["answers"]) <= set(q["options"])
            else:
                assert q["interaction"] == "article-input"
                assert q["inputFormat"]["instruction"] and q["inputFormat"]["placeholder"]
        if group["id"].startswith("5."):
            modes = Counter("choice" if q.get("options") else "input" for q in group["questions"])
            assert modes["choice"] >= 4 and modes["input"] >= 4
            assert group["allowNoArticle"]
    for q in u["exercises"][1]["questions"]:
        context = q["context"].lower()
        assert not any(hint in context for hint in [
            "выбери неопределённый артикль", "без артикля", "просто сообщи национальность",
            "нужен ли здесь артикль", "просто сообщи, кем работает"])
    contrast = [q for q in u["exercises"][1]["questions"] if q["interaction"] == "choice"]
    assert len(contrast) == 2
    assert all("___" not in q["prompt"] and len(q["options"]) == 2 for q in contrast)


def test_unit5_plural_alternatives_and_meaning_based_examples_are_not_marked_wrong():
    u = unit5()
    plural = u["exercises"][2]["questions"]
    coins = next(q for q in plural if q["prompt"] == "Tengo ___ monedas chinas.")
    books = next(q for q in plural if q["prompt"] == "En mi tienda vendo ___ libros.")
    flowers = u["sections"][2]["check"]["questions"][2]
    assert set(coins["answers"]) == {"unas", "Без артикля"}
    assert set(books["answers"]) == {"unos", "Без артикля"}
    assert set(flowers["answers"]) == {"unas", "Без артикля"}
    assert all(len(q["explain"]) >= 65 and len(q["answers"]) == 2 for q in [coins, books, flowers])
    assert {q["answers"][0] for q in u["exercises"][1]["questions"]} >= {"un", "una", "Без артикля"}


def test_unit5_fable_critical_warnings_are_resolved_not_suppressed():
    findings = pedagogical_unit(unit5(), "005_sin_articulo.json")
    critical = {"CONTEXT_LEAK", "CONTEXT_PREDICTS_ANSWER", "LONG_MODE_RUN",
                "NEVER_CORRECT_OPTION", "REPEATED_EXPLANATION"}
    assert not [f for f in findings if f.rule in critical], [(f.rule, f.group, f.question) for f in findings]
