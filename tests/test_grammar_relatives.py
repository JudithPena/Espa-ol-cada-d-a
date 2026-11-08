"""Coverage and preservation for the independently authored relative-clause units."""
import hashlib
import json
from pathlib import Path

from espanol.grammar import load_grammar


def unit(number):
    return next(u for u in load_grammar() if u['number'] == number)


def frozen(number, count):
    before = json.loads(Path(f'tests/data/grammar_before_unit{number}.json').read_text())
    assert len(before) == count
    for name, digest in before.items():
        assert hashlib.sha256((Path('content/grammar') / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest


def test_unit28_preserves_source_coverage_and_previous_lessons():
    frozen(28, 27)
    u = unit(28)
    assert [len(g['questions']) for g in u['exercises']] == [4, 10, 4, 8, 9]
    expected = {f'28.{g}.{i}' for g, count in [(1,10),(2,7),(3,8),(4,7)] for i in range(1,count+1)}
    assert {q['sourceRef'] for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra'} == expected
    assert u['exercises'][1]['questions'][4]['answers'] == ['el que','que']
    assert u['exercises'][1]['questions'][7]['answers'] == ['el que']
    assert u['exercises'][2]['questions'][2]['answers'] == ['con las que','con quienes','con que']
    assert 'запятыми' in u['sections'][1]['paragraphs'][-1]
    for g in u['exercises']:
        assert g['theorySections']
        for q in g['questions']:
            f = q.get('inputFormat', g['inputFormat'])
            assert f['instruction'] and f['placeholder']
            assert f.get('example') not in q['answers']
            assert ''.join(q['inputChars']) == 'áéíóúüñ'


def test_unit29_covers_all_source_positions_and_licenses_modern_variants():
    frozen(29, 28)
    u = unit(29)
    assert [len(g['questions']) for g in u['exercises']] == [8,3,6,9,4]
    expected = {f'29.{g}.{i}' for g, count in [(1,10),(2,6),(3,12)] for i in range(1,count+1)}
    questions = [q for g in u['exercises'] for q in g['questions']]
    assert {q['sourceRef'] for q in questions if q['sourceRef'] != 'extra'} == expected
    by_ref = {q['sourceRef']:q for q in questions}
    assert by_ref['29.1.3']['answers'] == ['cuya']
    assert by_ref['29.1.6']['answers'] == ['en cuyo']
    assert by_ref['29.1.10']['answers'] == ['para cuyas']
    assert by_ref['29.2.2']['answers'] == ['cuyo']
    assert by_ref['29.2.6']['answers'] == ['cuya']
    assert by_ref['29.3.6']['answers'] == ['adonde','a donde','donde','a la que','a que']
    assert by_ref['29.3.12']['answers'] == ['en la que','en que','cuando']
    for g in u['exercises']:
        assert g['theorySections']
        for q in g['questions']:
            f = q.get('inputFormat',g['inputFormat'])
            assert f['instruction'] and f['placeholder']
            assert f.get('example') not in q['answers']
            assert ''.join(q['inputChars']) == 'áéíóúüñ'
    assert [u['number'] for u in load_grammar()] == list(range(1,30))
