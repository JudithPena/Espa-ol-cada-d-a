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


def test_unit12_first_mini_check_covers_all_three_distances_without_changing_existing_items():
    from espanol.grammar import load_grammar
    unit = next(u for u in load_grammar() if u["number"] == 12)
    mini = unit["sections"][0]["check"]
    assert mini["id"] == "check-a"
    assert mini["revision"] == 2
    assert [q["distance"] for q in mini["questions"]] == ["near", "listener", "far"]
    assert [q["answers"] for q in mini["questions"]] == [["este"], ["esas"], ["aquel"]]
    assert mini["questions"][2]["options"] == ["aquella", "este", "aquel"]
    assert "ese" in mini["questions"][2]["explain"]
    assert "gDistance(q.distance, gUnit()?.number === 12)" in (Path(__file__).resolve().parents[1] / "espanol/grammar_player.js").read_text(encoding="utf-8")
    player = (Path(__file__).resolve().parents[1] / "espanol/grammar_player.js").read_text(encoding="utf-8")
    assert "function gDistanceArt(key)" in player
    assert "gdistance-dot" in player  # Legacy distance display preserved outside unit 12.
    styles = (Path(__file__).resolve().parents[1] / "espanol/site_template.html").read_text(encoding="utf-8")
    assert ".gdistance-illustrated .gdistance-art" in styles
