"""Source coverage and content boundaries for the sequential clitic lessons."""
import hashlib
import json
from pathlib import Path
import pytest
from espanol.grammar import load_grammar


def test_clitic_lessons_preserve_previous_content_and_explicit_input_formats():
    units = [u for u in load_grammar() if 37 <= u['number'] <= 39]
    assert units
    expected = {37: {1: 6, 2: 8, 3: 10, 4: 8}, 38: {1: 15, 2: 8, 3: 8}, 39: {1: 8, 2: 9, 3: 8, 4: 8}}
    for u in units:
        n = u['number']
        before = json.loads(Path(f'tests/data/grammar_before_unit{n}.json').read_text())
        assert len(before) == n - 1
        for name, digest in before.items():
            assert hashlib.sha256((Path('content/grammar') / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest
        refs = [q['sourceRef'] for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra']
        assert len(refs) == len(set(refs))
        assert set(refs) == {f'{n}.{g}.{i}' for g, count in expected[n].items() for i in range(1, count + 1)}
        for g in u['exercises']:
            assert g['theorySections'] and len(g['questions']) <= 15
            for q in g['questions']:
                fmt = q.get('inputFormat', g['inputFormat'])
                assert fmt['instruction'] and fmt['placeholder']
                assert ''.join(q['inputChars']) == 'áéíóúüñ'
                assert fmt.get('example') not in q['answers']
                if q.get('gapParts'):
                    assert len(q['gapWordCounts']) == len(q['gapParts']) - 1
                    assert sum(q['gapWordCounts']) == len(q['answers'][0].split())
                assert 'source' not in q, 'Use the visible sourceParts component'
                if q.get('tiles'):
                    assert q['tiles'] != q['answers'][0].split(), 'Do not give the answer in order'


def test_unit37_keeps_recipient_and_object_separate():
    u = next(u for u in load_grammar() if u['number'] == 37)
    qs = {q['sourceRef']: q for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra'}
    assert qs['37.1.2']['answers'] == ['se lo']  # plural parents, singular money
    assert qs['37.1.3']['answers'] == ['nos lo']  # answer to os
    assert qs['37.1.4']['answers'] == ['te las']  # answer to me
    assert qs['37.2.4']['answers'] == ['me la ha enseñado']  # usted -> me
    assert qs['37.3.7']['answers'] == ['se los']  # se + plural chocolates
    assert qs['37.4.4']['answers'] == ['a usted no se lo he enviado']
    assert 'a él no le han aprobado' in qs['37.4.7']['answerWarnings']
    assert qs['37.4.6']['answers'] == ['a ella la han aprobado']


def test_unit38_distinguishes_polite_address_from_feminine_third_person():
    u = next(u for u in load_grammar() if u['number'] == 38)
    qs = {q['sourceRef']: q for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra'}
    assert qs['38.1.3']['answers'] == ['la']
    assert qs['38.1.10']['answers'] == ['la', 'le']
    assert 'usted' in qs['38.1.14']['context']
    assert qs['38.1.14']['answers'] == ['la', 'le']
    assert qs['38.2.7']['answers'] == ['le']  # Pili, not plural teeth
    assert qs['38.3.5']['answers'] == ['lo le la']
    assert qs['38.3.7']['answers'] == ['lo la']


def test_unit39_joins_forms_and_explicitly_teaches_accent_sensitive_task():
    u = next(u for u in load_grammar() if u['number'] == 39)
    qs = {q['sourceRef']: q for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra'}
    assert [len(g['questions']) for g in u['exercises']] == [9, 10, 9, 8]
    assert qs['39.1.2']['answers'] == ['compradlo']
    assert qs['39.1.7']['answers'] == ['pásasela']  # agua remains feminine
    assert qs['39.2.2']['answers'] == ['devolvérmelo']
    assert qs['39.2.6']['answers'] == ['vendérselo']
    assert qs['39.3.5']['answers'][:2] == ['Están haciéndosela', 'Se la están haciendo']
    assert qs['39.3.6']['answers'][:2] == ['Está lavándoselo', 'Se lo está lavando']
    assert all(q['accentSensitive'] and not q.get('tiles') for q in u['exercises'][3]['questions'])
    assert all('ударения' in q['inputFormat']['instruction'] for q in u['exercises'][3]['questions'])


@pytest.mark.parametrize('feedback', [None, [], ['wrong'], ['yes', 'yes']])
def test_feedback_answers_cannot_show_an_unaccepted_or_duplicate_answer(tmp_path, feedback):
    unit = dict(id='fixture', sections=[], exercises=[dict(id='x', questions=[dict(
        prompt='x', answers=['yes'], explain='x', feedbackAnswers=feedback)])])
    (tmp_path / '001.json').write_text(json.dumps(unit), encoding='utf8')
    with pytest.raises(ValueError, match='feedbackAnswers'):
        load_grammar(tmp_path)
