"""Source coverage, answer contracts and isolation of the hay sequence."""
import hashlib
import json
from pathlib import Path
from espanol.grammar import load_grammar


def test_hay_source_coverage_and_previous_units():
    for u in load_grammar():
        n = u['number']
        if n not in (46, 47):
            continue
        counts = {46: [10, 10, 10, 8], 47: [10, 8, 17]}[n]
        before = json.loads(Path(f'tests/data/grammar_before_unit{n}.json').read_text())
        assert len(before) == n - 1
        for name, digest in before.items():
            assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest
        refs = [q['sourceRef'] for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra']
        assert len(refs) == len(set(refs))
        assert set(refs) == {f'{n}.{g}.{i}' for g, count in enumerate(counts, 1) for i in range(1, count+1)}
        for g in u['exercises']:
            assert g['limitedAttempt'] is True
            assert g['theorySections']
            assert len(g['questions']) <= 15
            for q in g['questions']:
                assert q['context'] and q['learningAction'] and q['explain']
                assert ''.join(q['inputChars']) == 'áéíóúüñ'
                if not q.get('options'):
                    fmt = q.get('inputFormat', g['inputFormat'])
                    assert fmt['instruction'] and fmt['placeholder']
        assert Path(f'docs/grammar_unit_{n}_plan.md').exists()
        for i, s in enumerate(u['sections']):
            assert s['check']['limitedAttempt'] is True
            assert s['check']['theorySections'] == [i]


def test_limited_attempt_requires_boolean(tmp_path):
    import pytest
    fixture = {'id': 'test', 'sections': [], 'exercises': [
        {'id': 'practice', 'limitedAttempt': 'yes', 'questions': []}]}
    (tmp_path/'001.json').write_text(json.dumps(fixture), encoding='utf8')
    with pytest.raises(ValueError, match='limitedAttempt must be boolean'):
        load_grammar(tmp_path)
