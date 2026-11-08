"""Regression checks for choices that require a decision instead of one repeated action."""
import json
from collections import Counter
from pathlib import Path

import pytest

from espanol.grammar import load_grammar


def test_profession_practice_contrasts_meanings_after_both_rules_are_taught():
    u = load_grammar()[4]
    g = u['exercises'][0]
    assert g['id'] == '5.1' and len(g['questions']) == 8
    assert u['learningOrder'].index('section:1') < u['learningOrder'].index('exercise:5.1')
    assert g['theorySections'] == [0, 1]
    assert {q['answers'][0] for q in g['questions']} == {'un', 'una', 'Без артикля'}
    assert any(not q.get('options') for q in g['questions'])
    assert any('quiere ser' in q['prompt'] for q in g['questions'])
    assert any(' son ' in q['prompt'] and q['answers'] == ['Без артикля'] for q in g['questions'])
    assert all(q['context'] and q['explain'] and q['translation'] for q in g['questions'])
    # Guessing "no article" or one fixed button cannot complete this exercise.
    assert not all('Без артикля' in q['answers'] for q in g['questions'])
    for position in range(5):
        assert not all(q.get('options', [])[position:position+1] and q['options'][position] in q['answers'] for q in g['questions'])
    plural = next(q for q in g['questions'] if ' son ' in q['prompt'])
    assert 'unas' in plural['options']


def test_other_flagged_series_require_different_decisions():
    units = load_grammar()
    food = units[4]['exercises'][2]['questions']
    assert {'un', 'una', 'unos', 'unas', 'Без артикля'} == {q['answers'][0] for q in food}
    names = units[7]['exercises'][0]['questions']
    assert next(q for q in names if q['prompt'].startswith('Buenos días'))['answers'] == ['Без артикля']
    assert next(q for q in names if '¿Dónde está' in q['prompt'])['answers'] == ['el']
    assert any(q['answers'] == ['las'] for q in names)
    addresses = units[7]['exercises'][1]['questions']
    assert {q['answers'][0] for q in addresses} == {'el', 'la', 'los', 'las'}
    time = units[8]['exercises'][0]['questions']
    assert {q['answers'][0].lower() for q in time} == {'son las', 'es la', 'a las', 'a la'}
    assert all(q.get('clock') for q in time)
    assert any(not q.get('options') for q in time)
    feminine = units[1]['sections'][4]['check']['questions']
    assert any(q['answers'] == ['el avión'] for q in feminine)
    assert any('Почему' in q['prompt'] for q in feminine)


def test_variety_audit_covers_every_group_and_exercises_require_different_answers():
    units = load_grammar()
    report = json.loads((Path(__file__).parents[1] / 'docs/grammar_exercise_variety_audit.json').read_text())
    assert len(report['units']) == 17
    for u, review in zip(units, report['units']):
        groups = [s['check'] for s in u['sections'] if s.get('check')] + u['exercises']
        assert review['unit'] == u['number']
        assert {g['id'] for g in groups} == {g['id'] for g in review['groups']}
        for g in groups:
            # Attempt-time shuffling, including distribution and sequence checks,
            # replaces restrictions on the unrendered source-array positions.
            if g in u['exercises']:
                assert len({q['answers'][0] for q in g['questions']}) > 1
    # Interleaving keeps all eight nationality models while removing the rigid three-question cycle.
    qs = units[13]['exercises'][0]['questions']
    assert len(set(q['clues'][0][0] for q in qs)) == 8
    assert set(Counter(q['clues'][0][0] for q in qs).values()) == {3}
    assert len(set(q['clues'][0][0] for q in qs[:3])) == 3
    assert not all(q['prompt'] == ['Ella es ___.', 'Ellos son ___.', 'Ellas son ___.'][i % 3] for i, q in enumerate(qs))


@pytest.mark.parametrize('revision', [0, -1, True, '2', None])
def test_invalid_content_revisions_are_rejected(tmp_path, revision):
    u = {'id': 'fixture', 'revision': revision, 'sections': [], 'exercises': []}
    (tmp_path / '001.json').write_text(json.dumps(u), encoding='utf-8')
    with pytest.raises(ValueError, match='revision'):
        load_grammar(tmp_path)
