"""Coverage, context and progress preservation for the ser/estar/tener sequence."""
import hashlib
import json
from pathlib import Path
from collections import Counter
from espanol.grammar import load_grammar


def test_ser_estar_tener_sources_formats_and_previous_units():
    counts = {42: [6, 10, 8], 43: [3, 8, 6, 5], 44: [9, 9, 10, 8], 45: [5, 7, 10]}
    for u in load_grammar():
        n = u['number']
        if n not in counts:
            continue
        before = json.loads(Path(f'tests/data/grammar_before_unit{n}.json').read_text())
        assert len(before) == n - 1
        for name, digest in before.items():
            assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest
        qs = [q for g in u['exercises'] for q in g['questions']]
        refs = [q['sourceRef'] for q in qs if q['sourceRef'] != 'extra']
        assert len(refs) == len(set(refs))
        assert set(refs) == {f'{n}.{g}.{i}' for g, count in enumerate(counts[n], 1) for i in range(1, count+1)}
        for g in u['exercises']:
            assert g['theorySections'] and len(g['questions']) <= 15
            for q in g['questions']:
                assert q['context'] and q['learningAction']
                assert ''.join(q['inputChars']) == 'áéíóúüñ'
                if not q.get('options'):
                    fmt = q.get('inputFormat', g['inputFormat'])
                    assert fmt['instruction'] and fmt['placeholder']
                if q.get('tiles'):
                    assert Counter(q['answers'][0].split()) <= Counter(q['tiles'])
                    assert q['tiles'] != q['answers'][0].split()
        assert Path(f'docs/grammar_unit_{n}_plan.md').exists()
