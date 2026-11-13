"""Visual and content coverage for the unit-12 demonstrative distance map."""
from pathlib import Path

from espanol.grammar import load_grammar


def test_unit12_theory_distance_map_has_complete_forms_and_context():
    unit = next(u for u in load_grammar() if u["number"] == 12)
    section = unit["sections"][0]
    assert section["distanceMap"]["title"] == "Как выбрать este, ese, aquel"
    assert section["presentation"] == "examples"
    assert len(section["wordGroups"]) == 3
    assert [len(g["words"]) for g in section["wordGroups"]] == [2, 1, 2]
    assert section["table"]["rows"] == [
        ["este", "este", "esta", "estos", "estas"],
        ["ese", "ese", "esa", "esos", "esas"],
        ["aquel", "aquel", "aquella", "aquellos", "aquellas"],
    ]
    assert "ese" in section["distanceMap"]["note"]
    assert all(not s.get("distanceMap") for s in unit["sections"][1:])
    assert [len(g["questions"]) for g in unit["exercises"]] == [8, 8, 9, 4]
    assert "В воспоминаниях нередко возможны оба варианта." in unit["sections"][2]["paragraphs"][-1]


def test_distance_map_is_opt_in_and_mobile_layout_is_present():
    root = Path(__file__).resolve().parents[1]
    player = (root / "espanol" / "grammar_player.js").read_text(encoding="utf-8")
    template = (root / "espanol" / "site_template.html").read_text(encoding="utf-8")
    assert "function gDemonstrativesDistance(section)" in player
    assert "section.distanceMap ? gDemonstrativesDistance(section)" in player
    assert "section.wordGroups && !section.distanceMap" in player
    assert "section.table && !section.distanceMap" in player
    assert ".gdist-axis" in template
    assert ".gdist-forms .gforms-mobile" in template
    assert "@media(max-width:600px)" in template
