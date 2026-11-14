"""Content-quality regressions from the 17-unit choice audit, not a new UI snapshot."""
import json
from pathlib import Path

import pytest

from espanol.grammar import load_grammar


def groups(unit):
    return [s['check'] for s in unit['sections'] if s.get('check')] + unit['exercises']


def test_audit_covers_all_units_and_offers_every_accepted_choice():
    units = load_grammar()
    audit = json.loads((Path(__file__).parent/'data/grammar_choice_audit.json').read_text(encoding='utf-8'))
    assert [u['unit'] for u in audit['units']] == list(range(1, 18))
    for unit, record in zip(units, audit['units']):
        total = sum(len(g['questions']) for g in groups(unit))
        if unit['number'] == 7:
            # This dated audit is a historical baseline, not a current count.
            assert record['reviewed'] == 75 and total == 45
        elif unit['number'] == 5:
            # Stage 5 editorial replacement has its own up-to-date tests.
            assert record['reviewed'] == 47 and total == 44
        elif unit['number'] == 13:
            # Historical Nov 8 audit counted 49; Stage 6 now has 48.
            assert record['reviewed'] == 49 and total == 48
        elif unit['number'] == 2:
            # Fable stage 8 supersedes the dated 73-question choice audit.
            assert record['reviewed'] == 73 and total == 57
        elif unit['number'] == 8:
            # Stage 7 supersedes the 68-question historical choice audit.
            assert record['reviewed'] == 68 and total == 58
        elif unit['number'] == 12:
            # The dated audit counted two questions in check-a. Unit 12 now checks
            # all three distances while preserving the original audit snapshot.
            assert record['reviewed'] == 37 and total == 38
        else:
            assert total == record['reviewed']
        for group in groups(unit):
            choices = [q for q in group['questions'] if q.get('options') and not q.get('guidedGaps')]
            assert all(set(q['answers']) <= set(q['options']) for q in choices)
            # Source order is not presentation order. Runtime distribution is checked
            # against persisted per-attempt plans in site_grammar.test.cjs.


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
    assert len(units) == 62
    for unit in units:
        for section in unit['sections']:
            check = section.get('check')
            if not check:
                continue
            assert 'inputFormat' not in check
            for q in check['questions']:
                assert len(q.get('options', [])) >= 2, (unit['id'], check['id'], q['prompt'])
                assert not any(q.get(key) for key in ('tiles', 'guidedGaps', 'gapParts'))
                assert set(q['answers']) <= set(q['options'])
                assert set(q['options']) - set(q['answers'])


def test_choices_must_offer_all_accepted_alternatives(tmp_path):
    fixture = {'id': 'fixture', 'sections': [], 'exercises': [{'id': 'a', 'questions': [{
        'prompt': 'rubí → ___', 'answers': ['rubíes', 'rubís'],
        'options': ['rubí', 'rubíes', 'rubies'], 'explain': 'Оба варианта правильные: rubíes и rubís.'
    }]}]}
    (tmp_path / '001.json').write_text(json.dumps(fixture), encoding='utf-8')
    with pytest.raises(ValueError, match='correct answer missing'):
        load_grammar(tmp_path)


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
