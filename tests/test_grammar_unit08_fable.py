"""Fable stage 7: unit 8 proper names, geographic articles, contractions and revisions."""
from collections import Counter

from espanol.grammar import load_grammar


def unit8():
    return next(u for u in load_grammar() if u["number"] == 8)


def groups(u):
    return [s["check"] for s in u["sections"]] + u["exercises"]


def test_id_routes_group_revisions_and_balanced_length():
    u = unit8()
    assert u["id"] == "008_nombres_propios"
    assert u["revision"] == 2
    assert [g["id"] for g in groups(u)] == [
        "check-a", "check-b", "check-c", "check-d", "8.1", "8.2", "8.3", "8.4"
    ]
    assert [g["revision"] for g in groups(u)] == [2, 2, 2, 2, 3, 3, 2, 2]
    assert u["learningOrder"] == [
        "section:0", "exercise:8.1", "section:1", "exercise:8.2",
        "section:2", "exercise:8.3", "section:3", "exercise:8.4", "summary"
    ]
    assert [g["theorySections"] for g in u["exercises"]] == [[0], [1], [2], [3]]
    assert [len(g["questions"]) for g in u["exercises"]] == [9, 10, 15, 12]
    assert [len(s["check"]["questions"]) for s in u["sections"]] == [3, 3, 3, 3]
    assert sum(len(g["questions"]) for g in groups(u)) == 58
    assert all(s["check"]["instruction"] for s in u["sections"])


def test_every_answer_is_reachable_in_existing_formats():
    u = unit8()
    for group in groups(u):
        prompts = []
        for q in group["questions"]:
            prompts.append(q["prompt"])
            assert q["context"] and q["explain"] and len(q["explain"]) >= 55, (group["id"], q["prompt"])
            if q.get("options"):
                assert q["interaction"] in ("choice", "gap-choice")
                assert all(a in q["options"] for a in q["answers"])
                assert len(q["options"]) == len({x.casefold() for x in q["options"]})
                assert len(q["options"]) >= 2
            else:
                assert q["interaction"] in ("article-input", "input")
                fmt = q.get("inputFormat", group.get("inputFormat"))
                assert fmt and fmt.get("placeholder") and fmt.get("instruction")
            if q["interaction"] == "input" and len(q["answers"][0].split()) == 2:
                assert "два слова" in q["inputFormat"]["instruction"].lower()
        assert len(prompts) == len(set(prompts)), group["id"]
    assert all(g.get("allowNoArticle") for g in (u["exercises"][0], u["exercises"][2]))


def test_81_comma_vocative_don_dona_and_plural_people():
    qs = uqs = unit8()["exercises"][0]["questions"]
    assert any("¿Está el doctor Rojo?" in q["answers"][0] for q in qs)
    assert any(q["prompt"] == "Buenos días, ___ doctora Vega." and
               q["answers"] == ["Без артикля"] for q in qs)
    assert any("doña Isabel" in q["prompt"] and q["answers"] == ["Без артикля"] for q in qs)
    assert any("doctoras Castro y Ramírez" in q["prompt"] and q["answers"] == ["las"] for q in qs)
    assert "запят" in " ".join(unit8()["sections"][0]["paragraphs"]).lower()


def test_82_base_noun_plural_and_address_line_vs_sentence():
    u = unit8()
    text = " ".join(u["sections"][1]["paragraphs"])
    assert "Calle Mayor, 5" in text and "Vivo en la calle Mayor" in text
    qs = u["exercises"][1]["questions"]
    assert len([q for q in qs if "teatro Real" in q["prompt"]]) == 1
    assert any("calles Mayor y Real" in q["prompt"] and q["answers"] == ["las"] for q in qs)
    assert any("museos de la ciudad" in q["prompt"] and q["answers"] == ["los"] for q in qs)
    assert any(q["interaction"] == "choice" and "calle Alcalá" in q["prompt"] for q in qs)


def test_83_four_geographic_categories_and_all_optional_answers():
    u = unit8()
    qs = u["exercises"][2]["questions"]
    assert len(qs) == 15
    for place, accepted in (
        ("Perú", {"Без артикля", "el"}),
        ("India", {"Без артикля", "la"}),
        ("Argentina", {"Без артикля", "la"}),
        ("Ecuador", {"Без артикля", "el"}),
    ):
        q = next(q for q in qs if place in q["prompt"])
        assert set(q["answers"]) == accepted, (place, q["answers"])
        assert q["interaction"] == "article-input"
        assert "допустим" in q["explain"].lower() or "можно" in q["explain"].lower() or "норматив" in q["explain"].lower()
    assert any("Habana" in q["prompt"] or "Habana" in q["answers"][0] for q in qs)
    assert any("Salvador" in q["prompt"] for q in qs)
    assert any("Ángeles" in q["prompt"] for q in qs)
    assert any("lago Titicaca" in q["prompt"] for q in qs)
    assert any("Pirineos" in q["prompt"] for q in qs)
    assert any("Amazonas" in q["prompt"] for q in qs)
    assert not any("Asia" in q["prompt"] or "Mancha" in q["prompt"] for q in qs)
    assert sum("lago Titicaca" in q["prompt"] for q in qs) == 2  # example + why, not 3 shifted gaps
    assert any(q["interaction"] == "article-input" and q["answers"] == ["Без артикля"] for q in qs)


def test_84_both_prepositions_and_spaced_proper_name_inputs():
    g = unit8()["exercises"][3]
    qmap = {q["prompt"]: q for q in g["questions"]}
    expected = {
        "Después de clase voy ___ museo.": "al",
        "Mi hermana vuelve ___ museo.": "del",
        "Mañana viajo ___ Salvador.": "a El",
        "Mi amigo viene ___ Cairo.": "de El",
        "Volvemos ___ Habana.": "de La",
    }
    for prompt, value in expected.items():
        q = qmap[prompt]
        assert q["answers"] == [value] and q["interaction"] == "input"
        assert "два слова" in q["inputFormat"]["instruction"].lower() if " " in value else "одно слово" in q["inputFormat"]["instruction"].lower()
    assert any("del museo / de El Cairo" in q["answers"][0] for q in g["questions"])
    assert any(q["interaction"] == "choice" and "Viajo a El Salvador" in q["answers"][0] for q in g["questions"])


def test_cognitive_actions_are_mixed_not_just_one_article_operation():
    u = unit8()
    stats = [Counter(q["interaction"] for q in g["questions"]) for g in u["exercises"]]
    assert stats == [
        Counter({"choice": 3, "gap-choice": 1, "article-input": 5}),
        Counter({"choice": 4, "article-input": 6}),
        Counter({"choice": 4, "gap-choice": 4, "article-input": 7}),
        Counter({"choice": 7, "input": 5}),
    ]
