"""Content-quality regressions from the 17-unit choice audit, not a new UI snapshot."""
import json
from pathlib import Path

import pytest

from espanol.grammar import load_grammar


def groups(unit):
    return [s['check'] for s in unit['sections'] if s.get('check')] + unit['exercises']


def test_audit_covers_all_units_and_does_not_offer_multiple_correct_buttons():
    units = load_grammar()
    audit = json.loads((Path(__file__).parent/'data/grammar_choice_audit.json').read_text(encoding='utf-8'))
    assert [u['unit'] for u in audit['units']] == list(range(1, 18))
    for unit, record in zip(units, audit['units']):
        assert sum(len(g['questions']) for g in groups(unit)) == record['reviewed']
        for group in groups(unit):
            choices = [q for q in group['questions'] if q.get('options') and not q.get('guidedGaps')]
            assert all(sum(option in q['answers'] for option in q['options']) == 1 for q in choices)
            # A systematic last-button shortcut must not return in longer practice groups.
            if len(choices) >= 4:
                assert sum(q['options'][-1] in q['answers'] for q in choices) / len(choices) <= .8


def test_plural_production_and_kinship_use_the_rule_instead_of_recognition():
    units = load_grammar()
    plural = units[2]
    assert all(not q.get('options') for q in plural['exercises'][0]['questions'])
    assert all(not q.get('options') for q in plural['exercises'][2]['questions'])
    family = units[0]['exercises'][2]['questions']
    assert set(family[1]['options']) == {'madre', 'abuela', 'hermana'}
    assert set(family[4]['options']) == {'hermano', 'nieto', 'hijo'}
    assert set(family[7]['options']) == {'hermana', 'tía', 'abuela'}


def test_optional_normative_forms_remain_accepted_without_becoming_false_choices():
    units = load_grammar()
    gorilla = units[1]['sections'][5]['check']['questions'][1]
    assert set(gorilla['answers']) == {'el gorila hembra', 'la gorila'}
    assert 'el gorila hembra' in gorilla['options']
    assert 'el gorila' not in [word[0] for group in units[1]['sections'][5]['wordGroups'] for word in group['words']]
    variants = units[2]['sections'][2]['check']['questions']
    assert all(q.get('options') for q in variants)
    assert {'menús','menúes'} <= set(variants[2]['answers'])


def test_all_mini_checks_offer_choices_without_typing():
    units = load_grammar()
    assert len(units) == 17
    for unit in units:
        for section in unit['sections']:
            check = section.get('check')
            if not check:
                continue
            assert 'inputFormat' not in check
            for q in check['questions']:
                assert len(q.get('options', [])) >= 2, (unit['id'], check['id'], q['prompt'])
                assert not any(q.get(key) for key in ('tiles', 'guidedGaps', 'gapParts'))
                assert len(set(q['options']) & set(q['answers'])) == 1


def test_choices_can_omit_accepted_alternatives_for_saved_typed_answers(tmp_path):
    fixture = {'id': 'fixture', 'sections': [], 'exercises': [{'id': 'a', 'questions': [{
        'prompt': 'rubí → ___', 'answers': ['rubíes', 'rubís'],
        'options': ['rubí', 'rubíes', 'rubies'], 'explain': 'Оба варианта правильные: rubíes и rubís.'
    }]}]}
    (tmp_path / '001.json').write_text(json.dumps(fixture), encoding='utf-8')
    assert load_grammar(tmp_path)[0]['exercises'][0]['questions'][0]['answers'] == ['rubíes', 'rubís']


@pytest.mark.parametrize('labels', [
    {'other':'Son las'}, {'la':''}, {'la':'Es la','las':'Es la'}, {'la':None}, ['Es la'],
])
def test_rejects_option_labels_that_hide_or_misidentify_answers(tmp_path, labels):
    fixture = {'id':'fixture','sections':[],'exercises':[{'id':'a','questions':[{
        'prompt':'___ una.', 'answers':['la'], 'options':['la','las'],
        'optionLabels':labels, 'explain':'Es la una.'}]}]}
    (tmp_path/'001.json').write_text(json.dumps(fixture),encoding='utf-8')
    with pytest.raises(ValueError,match='option labels'):
        load_grammar(tmp_path)
