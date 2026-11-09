"""Warnings annotate accepted answers without changing their identity or grammar context."""
import json

import pytest

from espanol.grammar import load_grammar


def test_warning_scope_is_explicit_and_preserves_feminine_and_plural_contexts():
    units = load_grammar()
    marked = [(u['number'], g['id'], i, q) for u in units
              for g in [*[s['check'] for s in u['sections'] if s.get('check')], *u['exercises']]
              for i, q in enumerate(g['questions']) if q.get('answerWarnings')]
    assert [(n, gid, i) for n, gid, i, _ in marked if n < 35] == [
        (1, '1.1', 6), (1, '1.2', 1), (4, '4.1', 11), (4, '4.3', 2), (4, '4.4', 3), (21, '21.2', 0)]
    assert [(gid, i) for n, gid, i, _ in marked if n == 35] == [
        ('35.1',0),('35.1',2),('35.1',5),
        ('35.2',1),('35.2',3),('35.2',4),('35.2',6),
        ('35.3',0),('35.3',6),('35.3',8),('35.4',4),('35.4',5)]
    for _, _, _, q in marked:
        for value, warning in q['answerWarnings'].items():
            assert value in q['answers']
            assert warning['preferred'] in q['answers']
            assert warning['preferred'] not in q['answerWarnings']
            assert warning['source'].startswith('https://www.rae.es/')
    for gid, word in [('4.1', 'aula'), ('4.3', 'hacha'), ('4.4', 'águila')]:
        q = next(q for g in units[3]['exercises'] if g['id'] == gid for q in g['questions'] if word in q['prompt'] and q['answers'] == ['un', 'una'])
        assert set(q['options']) == {'un', 'una', 'unos', 'unas'}
        assert q['answerWarnings']['una']['message'] == f'Допустимо, но лучше сказать un {word}.'
    # Immediate adjacency and singular number matter; these are ordinary green answers.
    checks = units[3]['sections'][2]['check']['questions']
    assert checks[0]['answers'] == ['unas'] and not checks[0].get('answerWarnings')
    assert checks[1]['answers'] == ['una'] and not checks[1].get('answerWarnings')


@pytest.mark.parametrize('warnings', [
    None, [], {}, {'wrong': {'preferred': 'un'}},
    {'una': {'preferred': 'una', 'message': 'm', 'explanation': 'e', 'source': 'https://www.rae.es/dpd/uno'}},
    {'una': {'preferred': 'unos', 'message': 'm', 'explanation': 'e', 'source': 'https://www.rae.es/dpd/uno'}},
    {'una': {'preferred': 'un', 'message': '', 'explanation': 'e', 'source': 'https://www.rae.es/dpd/uno'}},
    {'una': {'preferred': 'un', 'message': 'm', 'explanation': 'e', 'source': 'not a source'}},
    {'una': {'preferred': 'un', 'message': 'm', 'explanation': 'e'}},
    {'una': 'rare'},
])
def test_warning_metadata_rejects_unaccepted_variants_and_unusable_feedback(tmp_path, warnings):
    u = {'id': 'fixture', 'sections': [], 'exercises': [{'id': 'a', 'questions': [{
        'prompt': '___ hacha', 'answers': ['un', 'una'], 'explain': 'un hacha', 'answerWarnings': warnings}]}]}
    (tmp_path / '001.json').write_text(json.dumps(u), encoding='utf-8')
    with pytest.raises(ValueError, match='answer warnings'):
        load_grammar(tmp_path)
