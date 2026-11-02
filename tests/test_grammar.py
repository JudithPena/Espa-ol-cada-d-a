import json

import pytest

from espanol.grammar import load_grammar
from espanol.site import site_data


def test_unit_covers_supplied_page(course):
    unit, = site_data(course, {})["grammar"]
    assert unit["id"] == "001_el_hijo_la_hija"
    assert [len(g["questions"]) for g in unit["exercises"]] == [10, 15, 10]
    pictures = unit["exercises"][0]["questions"]
    assert all(q["image"].startswith("data:image/webp;base64,") and q["imageAlt"] for q in pictures)
    assert [q["prompt"] for q in pictures] == [f"№ {i}" for i in range(1, 11)]
    assert all(s.get("check") for s in unit["sections"])
    feminine = unit["exercises"][1]["questions"]
    assert feminine[1]["answers"] == ["jefa", "jefe"]
    assert feminine[-1]["answers"] == ["médica", "médico"]
    family = unit["exercises"][2]
    assert [b["child"] for b in family["family"]["branches"]] == ["Julio", "Laura"]
    assert family["questions"][2]["answers"] == ["hermana"]


def test_reject_answer_missing_from_options(tmp_path):
    unit, = load_grammar()
    unit["exercises"][0]["questions"][0]["answers"] = ["missing"]
    (tmp_path / "001.json").write_text(json.dumps(unit), encoding="utf-8")
    with pytest.raises(ValueError, match="correct answer missing"):
        load_grammar(tmp_path)
