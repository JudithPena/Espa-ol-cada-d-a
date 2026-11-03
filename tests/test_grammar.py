import json

import pytest

from espanol.grammar import load_grammar
from espanol.site import site_data


def test_unit_covers_supplied_page(course):
    unit = site_data(course, {})["grammar"][0]
    assert unit["id"] == "001_el_hijo_la_hija"
    assert [len(g["questions"]) for g in unit["exercises"]] == [10, 15, 10]
    pictures = unit["exercises"][0]["questions"]
    assert all(q["image"].startswith("data:image/webp;base64,") and q["imageAlt"] for q in pictures)
    assert [q["prompt"] for q in pictures] == [f"№ {i}" for i in range(1, 11)]
    assert all(s.get("check") for s in unit["sections"])
    feminine = unit["exercises"][1]["questions"]
    assert feminine[1]["answers"] == ["jefa", "jefe"]
    assert feminine[-1]["answers"] == ["médica"]
    assert feminine[12]["answers"] == ["dependienta", "dependiente"]
    assert pictures[6]["answers"] == ["la piloto", "la pilota"]
    family = unit["exercises"][2]
    assert [b["child"] for b in family["family"]["branches"]] == ["Julio", "Laura"]
    assert family["questions"][2]["answers"] == ["hermana"]
    assert len(family["family"]["portraits"]) == 10
    assert all(image.startswith("data:image/webp;base64,") for image in family["family"]["portraits"].values())
    assert [(b["at"], b["person"]) for b in family["questionBlocks"]] == [(0, "Julio"), (5, "Silvia")]
    assert family["questions"][0]["context"] == "1. Кем Luis приходится Julio?"
    assert family["questions"][5]["context"] == "6. Кем Luis приходится Silvia?"


def test_reject_answer_missing_from_options(tmp_path):
    unit = load_grammar()[0]
    unit["exercises"][0]["questions"][0]["answers"] = ["missing"]
    (tmp_path / "001.json").write_text(json.dumps(unit), encoding="utf-8")
    with pytest.raises(ValueError, match="correct answer missing"):
        load_grammar(tmp_path)


def test_second_unit_covers_pages_and_current_norm():
    first, unit = load_grammar()[:2]
    assert unit['id'] == '002_el_libro_la_mesa'
    assert [len(g['questions']) for g in unit['exercises']] == [32, 6, 10]
    assert len(unit['sections']) == 7
    assert all(s.get('check') for s in unit['sections'])
    classification = unit['exercises'][0]['questions']
    assert len({q['prompt'] for q in classification}) == 32
    assert next(q for q in classification if q['prompt'] == '___ radio')['translation'] == 'радиоприёмник в Испании'
    assert next(q for q in classification if q['prompt'] == '___ mano')['answers'] == ['la']
    assert next(q for q in classification if q['prompt'] == '___ problema')['answers'] == ['el']
    animals = unit['sections'][-2]
    fixed = [w[0] for g in animals['wordGroups'] for w in g['words']]
    assert 'el conejo' not in fixed and 'el ratón' not in fixed
    assert 'la coneja' in unit['sections'][-1]['schemes'][0]['to']
    pictures = unit['exercises'][2]['questions']
    assert all(q['image'].startswith('data:image/webp;base64,') and q['imageAlt'] for q in pictures)
    assert pictures[4]['answers'] == ['el gorila']
    assert pictures[-1]['answers'] == ['la nariz']
    assert unit['exercises'][1]['questions'][1]['answers'] == ['caballo']
    assert first['id'] != unit['id']


def test_third_unit_covers_plural_rules_and_all_supplied_tasks():
    unit = load_grammar()[2]
    assert unit['id'] == '003_libro_libros'
    assert [len(g['questions']) for g in unit['exercises']] == [18, 10, 10]
    assert len(unit['sections']) == 9
    variants = unit['sections'][2]['check']['questions']
    assert variants[0]['answers'] == ['rubíes', 'rubís']
    assert variants[1]['answers'] == ['bambúes', 'bambús']
    plural = {q['prompt']: q['answers'] for q in unit['exercises'][0]['questions']}
    assert plural['pantalones'] == ['pantalones']
    assert plural['jueves'] == ['jueves']
    assert plural['autobús'] == ['autobuses']
    assert plural['día'] == ['días']
    counting = unit['exercises'][1]['questions']
    assert [q['pictureCount'] for q in counting] == [1, 2, 1, 1, 3, 4, 2, 5, 3, 2]
    assert all(q['image'].startswith('data:image/webp;base64,') for q in counting)
    assert 'unas gafas' in counting[2]['answers'] and '1 gafas' not in counting[2]['answers']
    assert '2 botellas' in counting[1]['answers'] and 'dos botellas' in counting[1]['answers']
    assert '3 lápices' in counting[4]['answers']
    rewriting = unit['exercises'][2]['questions']
    assert all(len(q['sourceParts']) == 3 and q['sourceParts'][1] for q in rewriting)
    assert [q['answers'][0] for q in rewriting] == ['hijos', 'abuelos', 'amigos', 'hermanos', 'padres', 'reyes', 'alumnos', 'profesores', 'tíos', 'bailarines']
