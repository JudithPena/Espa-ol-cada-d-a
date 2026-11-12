"""Question identity and progress compatibility across the 17-unit UI revision."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from espanol.grammar import GRAMMAR, load_grammar


def test_redesign_preserves_all_question_keys_indices_and_accepted_answers():
    snapshots = json.loads((Path(__file__).parent / 'data/grammar_question_signatures.json').read_text(encoding='utf-8'))
    for unit in load_grammar():
        groups = [*[s['check'] for s in unit['sections'] if s.get('check')], *unit['exercises']]
        signature = {'id': unit['id'], 'groups': [
            {'id': g['id'], 'questions': [[q['prompt'], q['answers'], q.get('sourceRef')] for q in g['questions']]}
            for g in groups]}
        assert hashlib.sha256(json.dumps(signature, ensure_ascii=False, sort_keys=True).encode()).hexdigest() == snapshots[str(unit['number'])]


def test_all_units_interleave_theory_with_practice_and_keep_independent_writing():
    units = load_grammar()
    assert len(units) == 55
    for unit in units:
        routes = unit['learningOrder']
        practice = next(i for i, r in enumerate(routes) if r.startswith('exercise:'))
        assert any(r.startswith('section:') for r in routes[practice+1:]), unit['number']
        assert routes[-1] == 'summary'
        assert all(s['paragraphs'] and s['presentation'] for s in unit['sections'])
    questions = [q for u in units for g in u['exercises'] for q in g['questions']]
    assert sum(bool(q.get('tiles')) for q in questions) == 189  # Stage 6: +2 unit-13 word-bank tasks
    assert sum(not q.get('options') and not q.get('tiles') for q in questions) > 100
    assert all(2 <= len(q['options']) <= 6 for q in questions if q.get('options'))
    for q in questions:
        if q.get('tiles'):
            assert not (Counter(q['answers'][0].split()) - Counter(q['tiles']))


def test_story_context_does_not_reveal_the_current_completed_sentence():
    unit = next(u for u in load_grammar() if u['number'] == 7)
    for q in unit['exercises'][0]['questions']:
        current = q['prompt'].replace('___', q['answers'][0]).casefold()
        assert current not in ''.join(q.get('sourceParts', [])).casefold()


@pytest.mark.parametrize('tiles', [['la', 'más'], ['la', 'más', 'sana', 'y', 'fresca'], [None], []])
def test_invalid_word_bank_cannot_make_a_question_impossible(tmp_path, tiles):
    unit = {'id':'fixture', 'sections':[], 'exercises':[{'id':'a','questions':[{
        'prompt':'Completa', 'answers':['la más sana y la más fresca'], 'explain':'Проверка',
        'interaction':'build', 'tiles':tiles}]}]}
    (tmp_path/'001.json').write_text(json.dumps(unit), encoding='utf-8')
    with pytest.raises(ValueError, match='complete answer'):
        load_grammar(tmp_path)


@pytest.mark.parametrize('frame', [
    {'parts':['',' sana'], 'choices':[['el','los']]},
    {'parts':['',' sana'], 'choices':[['la']]},
    {'parts':[''], 'choices':[['el','la']]},
])
def test_guided_gaps_require_a_reachable_accepted_answer(tmp_path, frame):
    unit = {'id':'fixture', 'sections':[], 'exercises':[{'id':'a','questions':[{
        'prompt':'Completa ___', 'answers':['la sana'], 'explain':'Проверка',
        'guidedGaps':frame}]}]}
    (tmp_path/'001.json').write_text(json.dumps(unit), encoding='utf-8')
    with pytest.raises(ValueError, match='guided gaps'):
        load_grammar(tmp_path)
