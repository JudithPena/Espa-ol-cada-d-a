"""Fable stage 8: evidence that unit 2 tests understanding, alternatives and picture names."""

from collections import Counter

from espanol.grammar import load_grammar


def unit2():
    return next(u for u in load_grammar() if u["number"] == 2)


def groups(unit):
    return [section["check"] for section in unit["sections"]] + unit["exercises"]


def test_stage8_preserves_id_routes_and_invalidates_edited_groups():
    unit = unit2()
    assert unit["id"] == "002_el_libro_la_mesa"
    assert unit["revision"] == 2
    assert [g["id"] for g in groups(unit)] == [
        "check-a", "check-b", "check-c", "check-d", "check-e", "check-f", "check-g",
        "2.1", "2.2", "2.3"
    ]
    assert [g["revision"] for g in groups(unit)] == [2, 2, 2, 2, 3, 2, 2, 2, 2, 2]
    assert unit["learningOrder"] == [
        "section:0", "section:1", "section:2", "section:3", "section:4",
        "exercise:2.1", "section:5", "section:6", "exercise:2.2",
        "exercise:2.3", "summary"
    ]
    assert [len(s["check"]["questions"]) for s in unit["sections"]] == [3] * 7
    assert [len(g["questions"]) for g in unit["exercises"]] == [15, 11, 10]
    assert sum(len(g["questions"]) for g in groups(unit)) == 57


def test_first_exercise_asks_for_reasons_and_independent_noun_phrases():
    unit = unit2()
    exercise = unit["exercises"][0]
    assert "Распредели" not in exercise["title"]
    assert Counter(q["interaction"] for q in exercise["questions"]) == {
        "gap-choice": 2, "choice": 5, "article-input": 7, "input": 1
    }
    assert all("radio" not in q["prompt"] for q in exercise["questions"])
    intro_words = {word for group in exercise["introGroups"] for word, _ in group["words"]}
    assert "el cine" not in intro_words and "la atención" not in intro_words
    for q in exercise["questions"][:4]:
        assert not any(word in q["prompt"] for word in ("teléfono", "silla"))
    questions = exercise["questions"]
    assert any("la foto" in q["prompt"] and "fotografía" in q["answers"][0] for q in questions)
    assert any(q["answers"] == ["la mano"] and "Исправь" in q["prompt"] for q in questions)
    assert any(q["interaction"] == "input" and q["answers"] == ["el teléfono"] for q in questions)
    assert any("la cama" in q["prompt"] and "el problema" in q["prompt"] for q in questions)
    assert any("la leche" in q["prompt"] or "la leche" in q["explain"] for q in unit["sections"][3]["check"]["questions"])
    assert "обычно" in " ".join(unit["sections"][2]["paragraphs"]).lower() or "часто" in " ".join(unit["sections"][2]["paragraphs"]).lower()


def test_animals_are_gender_sex_and_species_not_six_word_pairs():
    unit = unit2()
    exercise = unit["exercises"][1]
    assert len(exercise["questions"]) == 11
    assert any("serpiente macho" in q["prompt"] and q["answers"] == ["la"] for q in exercise["questions"])
    assert any("tiburón hembra" in q["prompt"] and q["answers"] == ["el"] for q in exercise["questions"])
    assert any("jirafa macho" in q["prompt"] and "Род слова jirafa" in q["answers"][0] for q in exercise["questions"])
    assert any(q["answers"] == ["la perra"] and q["interaction"] == "input" for q in exercise["questions"])
    assert any(set(q["answers"]) == {"el gorila", "la gorila"} for q in exercise["questions"])
    assert set(unit["sections"][5]["check"]["questions"][1]["answers"]) == {"el gorila hembra", "la gorila"}
    assert all("gorilo" not in q["answers"] for g in groups(unit) for q in g["questions"])


def test_all_pictures_require_a_learner_written_article_and_noun():
    pictures = unit2()["exercises"][2]
    assert len(pictures["questions"]) == 10
    assert pictures["vocabulary"]["rows"]
    assert len({q["image"] for q in pictures["questions"]}) == 10
    assert all(q["imageAlt"] and q["interaction"] == "input" and not q.get("options")
               for q in pictures["questions"])
    assert all(q["answers"] and all(len(a.split()) == 2 for a in q["answers"])
               for q in pictures["questions"])
    assert pictures["questions"][1]["answers"] == ["el tren"]
    assert pictures["questions"][7]["answers"] == ["el tenedor"]
    assert pictures["questions"][0]["answers"] == ["el árbol"]
    assert set(pictures["questions"][4]["answers"]) == {"el gorila", "la gorila"}
    assert "пол" in pictures["questions"][4]["imageAlt"]


def test_correct_answer_choices_and_instructions_are_consistent():
    for group in groups(unit2()):
        assert group["instruction"]
        prompts = [q["prompt"] for q in group["questions"]]
        assert len(prompts) == len(set(prompts)), group["id"]
        for q in group["questions"]:
            assert q["context"] and q["explain"], (group["id"], q["prompt"])
            assert len(q["explain"]) >= 50, (group["id"], q["prompt"])
            if q.get("options"):
                assert len(q["options"]) == len(set(q["options"]))
                assert all(a in q["options"] for a in q["answers"])
            else:
                fmt = q.get("inputFormat", group.get("inputFormat"))
                assert fmt and fmt.get("instruction") and fmt.get("placeholder")
