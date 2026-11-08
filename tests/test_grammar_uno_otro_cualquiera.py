"""Coverage, ambiguity and progress safety for the single-unit 21 addition."""
import hashlib
import json
from pathlib import Path

from espanol.grammar import load_grammar


def unit21():
    return next(u for u in load_grammar() if u['number'] == 21)


def test_unit21_covers_every_supplied_position_and_interleaves_its_own_theory():
    u = unit21()
    assert u['id'] == '021_uno_otro_cualquiera'
    assert [len(g['questions']) for g in u['exercises']] == [8, 5, 8, 9]
    assert u['learningOrder'] == [stage for i, g in enumerate(u['exercises'])
                                  for stage in [f'section:{i}', f"exercise:{g['id']}"]] + ['summary']
    for i, (g, count) in enumerate(zip(u['exercises'], [8, 5, 8, 5])):
        assert g['theorySections'] == [i]
        assert {q['sourceRef'] for q in g['questions'] if q['sourceRef'] != 'extra'} == {
            f"{g['id']}.{n}" for n in range(1, count + 1)}
        for q in g['questions']:
            assert q['context'] and q['explain']
            assert ''.join(q['inputChars']) == 'áéíóúüñ'
            f = q.get('inputFormat', g['inputFormat'])
            assert f['instruction'] and f['placeholder']
            assert f.get('example') not in q['answers'], 'Do not give away the answer in format help'
    assert all(len(s['check']['questions']) == 2 for s in u['sections'])
    assert sum(bool(q.get('tiles')) for g in u['exercises'] for q in g['questions']) == 2


def test_unit21_disambiguates_addition_replacement_group_and_arbitrary_choice():
    u = unit21()
    a, b, c, d = [g['questions'] for g in u['exercises']]
    assert [q['answers'][0] for q in a] == ['una', 'otra', 'un', 'otra', 'otros', 'una', 'otras', 'otra']
    assert 'первый' in a[0]['context'] and 'уже' in a[3]['context']
    assert b[1]['answers'] == ['cualquiera de'] and b[3]['answers'] == ['cualquiera de']
    assert b[2]['answers'] == ['cualquier'] and 'día' in b[2]['prompt']
    assert c[2]['answers'] == ['otros'] and c[5]['answers'] == ['otras']
    assert c[4]['answers'] == ['uno de'] and 'одним из' in c[4]['context']
    assert c[6]['answers'] == ['cualquiera de', 'una cualquiera de']
    assert c[7]['answers'] == ['otros'] and 'ещё' in c[7]['context']
    assert d[2]['answers'] == ['cualquiera', 'uno cualquiera']
    assert [q['answers'][0] for q in d[5:7]] == ['otra bolsa', 'cualquiera de estos libros']
    # A regional feminine form is not used as a false distractor.
    w = b[0]['answerWarnings']['cualquiera']
    assert w['preferred'] == 'cualquier' and w['source'] == 'https://www.rae.es/dpd/cualquiera'


def test_existing_twenty_units_are_unchanged_and_later_units_not_started():
    baseline = json.loads(Path('tests/data/grammar_before_unit21.json').read_text())
    assert len(baseline) == 20
    for name, digest in baseline.items():
        assert hashlib.sha256((Path('content/grammar') / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest
    assert [u['number'] for u in load_grammar()] == list(range(1, 22))
