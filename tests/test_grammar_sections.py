"""Разделы грамматики как у Мёрфи: content/grammar/sections.json."""
import json

import pytest

from espanol.grammar import GRAMMAR, load_grammar, load_grammar_sections

CATALOG = json.loads((GRAMMAR / "sections.json").read_text(encoding="utf-8"))
NUMBERS = {int(p.name.split("_", 1)[0]) for p in GRAMMAR.glob("[0-9]*.json")}


def test_sections_cover_the_whole_book_once_in_order():
    listed = [n for s in CATALOG["sections"] for n in s["units"]]
    assert listed == list(range(1, 127))
    assert all(s["title"] and s["units"] for s in CATALOG["sections"])


def test_planned_entries_are_only_for_units_not_yet_written():
    planned = {p["number"] for p in CATALOG["planned"]}
    # Новый юнит: добавьте файл и уберите его строку из planned.
    assert not planned & NUMBERS, sorted(planned & NUMBERS)
    assert planned | NUMBERS == set(range(1, 127))


def test_site_sections_put_every_real_unit_in_place():
    units = load_grammar()
    sections = load_grammar_sections(units)
    ids = [e["id"] for s in sections for e in s["units"] if "id" in e]
    assert sorted(ids) == sorted(u["id"] for u in units)
    soon = [e for s in sections for e in s["units"] if "id" not in e]
    assert all(e["title"] and e["subtitle"] for e in soon)


def test_unit_without_section_or_title_breaks_the_build(tmp_path):
    bad = dict(CATALOG, sections=CATALOG["sections"][1:])  # без юнитов 1–3
    path = tmp_path / "sections.json"
    path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        load_grammar_sections(load_grammar(), path)
