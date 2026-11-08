"""Coverage and ambiguity checks for the sequential 22–24 additions."""
import hashlib
import json
from pathlib import Path
from espanol.grammar import load_grammar


def unit(n):
    return next(u for u in load_grammar() if u['number'] == n)


def test_unit22_retains_all_source_situations_and_explicit_format():
    u = unit(22)
    assert [len(g['questions']) for g in u['exercises']] == [7, 8, 10, 8]
    expected = {f'22.{g}.{i}' for g, count in [(1, 7), (2, 7), (3, 8), (4, 6)] for i in range(1, count+1)}
    assert {q['sourceRef'] for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra'} == expected
    assert 'точная ступень' in u['sections'][2]['paragraphs'][0]
    assert u['exercises'][0]['questions'][6]['answers'] == ['poco', 'poca']
    assert u['exercises'][2]['questions'][3]['answers'] == ['bastante gente']
    assert u['exercises'][3]['questions'][1]['answers'] == ['suficientes', 'bastantes']
    assert u['exercises'][3]['questions'][2]['answers'] == ['suficiente', 'bastante']
    for i, g in enumerate(u['exercises']):
        assert g['theorySections'] == [i]
        for q in g['questions']:
            f = q.get('inputFormat', g['inputFormat'])
            assert f['instruction'] and f['placeholder']
            assert f.get('example') not in q['answers']
            assert ''.join(q['inputChars']) == 'áéíóúüñ'


def test_completed_content_is_frozen_before_unit22():
    baseline = json.loads(Path('tests/data/grammar_before_unit22.json').read_text())
    assert len(baseline) == 24
    for name, digest in baseline.items():
        assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest


def test_unit23_covers_people_things_negation_and_all_dialogue_fields():
    u = unit(23)
    assert [len(g['questions']) for g in u['exercises']] == [8, 13, 8]
    expected = {f'23.{g}.{i}' for g, count in [(1, 8), (2, 10), (3, 6)] for i in range(1, count+1)}
    assert {q['sourceRef'] for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra'} == expected
    assert u['exercises'][0]['questions'][3]['answers'] == ['No hay nadie']
    assert 'диван' in u['exercises'][0]['questions'][3]['context']
    assert [q['answers'][0] for q in u['exercises'][1]['questions'][:10]] == ['alguien','algo','algo','nada','alguien','nadie','alguien','algo','nada','nadie']
    dialogs = u['exercises'][2]['questions'][:6]
    assert sum(len(q['gapWordCounts']) if q.get('gapParts') else 1 for q in dialogs) == 9
    assert dialogs[0]['gapWordCounts'] == [2, 2]
    assert dialogs[2]['answers'] == ['nada algo de']
    for i,g in enumerate(u['exercises']):
        assert g['theorySections'] == [i]
        for q in g['questions']:
            assert q.get('inputFormat', g['inputFormat'])['instruction']
            assert ''.join(q['inputChars']) == 'áéíóúüñ'


def test_unit22_is_frozen_before_unit23():
    baseline = json.loads(Path('tests/data/grammar_before_unit23.json').read_text())
    assert len(baseline) == 25
    for name, digest in baseline.items():
        assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest


def test_unit24_covers_original_positions_with_short_target_gaps():
    u = unit(24)
    assert [len(g['questions']) for g in u['exercises']] == [6,6,12,9]
    expected = {f'24.{g}.{i}' for g,count in [(1,9),(2,10),(3,8)] for i in range(1,count+1)}
    assert {q['sourceRef'] for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra'} == expected
    for q in u['exercises'][2]['questions'][:10]:
        assert q['gapWordCounts'] == [1,1]
        assert len(q['gapParts']) == 3
        assert q['facts']['items'] and len(q['answers'][0].split()) == 2
    assert u['exercises'][1]['questions'][4]['answers'] == ['tanta']
    assert u['exercises'][3]['questions'][7]['answers'] == ['tanto como tú']
    assert u['exercises'][3]['questions'][8]['answers'] == ['tantas','tantas como tú']
    assert 'другой смысл' in u['sections'][3]['paragraphs'][2]
    for i,g in enumerate(u['exercises']):
        assert g['theorySections'] == [i]
        for q in g['questions']:
            f = q.get('inputFormat', g['inputFormat'])
            assert f['instruction'] and f['placeholder']
            assert f.get('example') not in q['answers']


def test_unit23_is_frozen_before_unit24_and_gap_in_course_is_closed():
    baseline = json.loads(Path('tests/data/grammar_before_unit24.json').read_text())
    assert len(baseline) == 26
    for name, digest in baseline.items():
        assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest
    assert [u['number'] for u in load_grammar()] == list(range(1,28))
