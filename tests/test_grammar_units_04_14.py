"""Coverage and normative alternatives for the eleven supplied grammar units."""
from collections import defaultdict

import pytest

from espanol.grammar import load_grammar


SOURCE_ROWS = {
    4: [15, 10, 12, 10], 6: [15, 8, 6, 10],
    # Unit 5 has Fable Stage 5 coverage tests instead of frozen source-row counts.
    # Unit 7 is deliberately redesigned in Fable stage 4; see test_grammar_unit07_fable.py.
    # Unit 8 Stage 7 replaces dated textbook tasks; validated by dedicated tests.
    9: [8, 12, 6, 4],
    10: [8, 15, 8], 11: [10, 8, 10], 12: [8, 8, 8, 4],
    # Unit 13 has Fable stage 6 tests, rather than frozen textbook row coverage.
    14: [8, 8, 8],
}


def test_all_supplied_tasks_survive_adaptation_and_have_clear_gaps():
    units = load_grammar()
    assert [u['number'] for u in units] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50]
    for u in units:
        if u['number'] not in SOURCE_ROWS:
            continue
        coverage = defaultdict(set)
        for g in u['exercises']:
            assert g['instruction'] and g['preview']
            for q in g['questions']:
                assert q['prompt'].count('___') == 1
                assert q['context']
                assert 'учебник' not in str(q).lower()
                ref = q['sourceRef']
                if ref != 'extra':
                    number, exercise, row = map(int, ref.split('.'))
                    assert number == u['number']
                    coverage[exercise].add(row)
                if q.get('options'):
                    # Case alone must never distinguish a right and wrong article.
                    assert len({o.casefold() for o in q['options']}) == len(q['options'])
        for ex, count in enumerate(SOURCE_ROWS[u['number']], 1):
            assert coverage[ex] == set(range(1, count + 1)), (u['number'], ex)
        assert u['learningOrder'][0] == 'section:0'
        assert u['learningOrder'][-1] == 'summary'
        assert all(s['check']['questions'] for s in u['sections'])


def test_valid_variants_are_not_rejected_as_wrong():
    by_number = {u['number']: u for u in load_grammar()}
    questions = lambda n: [q for g in by_number[n]['exercises'] for q in g['questions']]
    assert next(q for q in questions(4) if q['prompt'] == '___ aula')['answers'] == ['un', 'una']
    assert next(q for q in questions(4) if q['prompt'] == '___ hacha')['answers'] == ['un', 'una']
    assert next(q for q in questions(8) if 'trabaja en ___ India' in q['prompt'])['answers'] == ['la', 'Без артикля']
    assert next(q for q in questions(8) if 'vive en ___ Perú' in q['prompt'])['answers'] == ['Без артикля', 'el']
    assert next(q for q in questions(12) if q['prompt'] == '___ árboles son muy altos.')['answers'] == ['aquellos', 'esos']
    iranian = [q for q in questions(14) if q['clues'][0][0] == 'iraní']
    assert [q['answers'] for q in iranian] == [['iraní'], ['iraníes', 'iranís'], ['iraníes', 'iranís']]
    assert next(q for q in questions(13) if 'dos faldas ___' in q['prompt'])['answers'] == ['marrones']


@pytest.mark.parametrize('clock', [{'hour': 24, 'minute': 0}, {'hour': 3, 'minute': 60}, {'hour': 3.5, 'minute': 0}, []])
def test_reject_invalid_clock_data(tmp_path, clock):
    import json
    u = next(u for u in load_grammar() if u['number'] == 9)
    for section in u['sections']:
        section.pop('illustration', None)
    u['exercises'][0]['questions'][0]['clock'] = clock
    (tmp_path/'009.json').write_text(json.dumps(u), encoding='utf-8')
    with pytest.raises(ValueError, match='valid hour and minute'):
        load_grammar(tmp_path)
