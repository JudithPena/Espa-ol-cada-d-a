"""Source coverage and independent-course boundaries for unit 36."""
import hashlib
import json
from pathlib import Path

from espanol.grammar import load_grammar


def test_unit36_covers_both_pages_and_keeps_previous_units():
    before = json.loads(Path('tests/data/grammar_before_unit36.json').read_text())
    assert len(before) == 35
    for name, digest in before.items():
        data = (Path('content/grammar') / name).read_bytes().replace(b'\r\n', b'\n')
        assert hashlib.sha256(data).hexdigest() == digest
    u = next(u for u in load_grammar() if u['number'] == 36)
    assert [len(g['questions']) for g in u['exercises']] == [8, 12, 9]
    refs = [q['sourceRef'] for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra']
    assert len(refs) == len(set(refs)) == 26
    assert set(refs) == {f'36.{g}.{i}' for g, n in [(1, 7), (2, 10), (3, 9)] for i in range(1, n + 1)}
    assert len(u['sections']) == 3
    assert all(len(s['check']['questions']) == 2 for s in u['sections'])
    for g in u['exercises']:
        assert g['theorySections'] and len(g['questions']) < 15
        for q in g['questions']:
            fmt = q.get('inputFormat', g['inputFormat'])
            assert fmt['instruction'] and fmt['placeholder']
            assert ''.join(q['inputChars']) == 'áéíóúüñ'
            assert fmt.get('example') not in q['answers']
    assert {q['answers'][0] for q in u['exercises'][0]['questions']} == {'me', 'te', 'le', 'nos', 'os'}
    # The recipient, not the gender or the number of presents, controls le(s).
    assert u['sections'][0]['check']['questions'][0]['answers'] == ['Le']
    assert u['sections'][0]['check']['questions'][1]['answers'] == ['Les']
    assert all('gapWordCounts' in q for q in u['exercises'][2]['questions'])


def test_unit36_explicitly_distinguishes_speaker_address_and_third_person():
    u = next(u for u in load_grammar() if u['number'] == 36)
    qs = {q['sourceRef']: q for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra'}
    assert qs['36.2.2']['answers'] == ['no me ha dicho nada']
    assert qs['36.2.5']['answers'] == ['no te ha dicho nada']
    assert qs['36.2.6']['answers'] == ['no os han preguntado nada']
    assert qs['36.2.8']['answers'] == ['no nos han dado nada']
    assert qs['36.2.10']['answers'] == ['no les han regalado nada']
    assert qs['36.3.2']['answers'] == ['les nos']
    assert qs['36.3.6']['answers'] == ['le me']
    assert qs['36.3.8']['answers'] == ['nos os']
    assert 'может быть необязательным' in ' '.join(u['sections'][2]['paragraphs'])
