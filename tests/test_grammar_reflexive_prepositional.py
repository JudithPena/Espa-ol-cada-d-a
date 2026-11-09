"""Source coverage, explicit context and varied learning actions in units 40–41."""
import hashlib
import json
from pathlib import Path
from collections import Counter
from espanol.grammar import load_grammar


def test_new_pronoun_units_cover_sources_and_preserve_previous_lessons():
    expected = {40: [15, 8, 12], 41: [8, 7, 7, 8]}
    for u in [u for u in load_grammar() if u['number'] in expected]:
        n = u['number']
        before = json.loads(Path(f'tests/data/grammar_before_unit{n}.json').read_text())
        assert len(before) == n - 1
        for name, digest in before.items():
            # Both 40 and 41 are requested targets. Final copy-editing of one
            # distractor in 40 is recorded in its report; protect every other unit.
            if n == 41 and name.startswith('040_'):
                continue
            assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest
        qs = [q for g in u['exercises'] for q in g['questions']]
        refs = [q['sourceRef'] for q in qs if q['sourceRef'] != 'extra']
        assert len(refs) == len(set(refs))
        assert set(refs) == {f'{n}.{g}.{i}' for g, count in enumerate(expected[n], 1) for i in range(1, count+1)}
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


def test_unit40_disambiguates_reflexive_reciprocal_and_nonreflexive_contexts():
    u = next(u for u in load_grammar() if u['number'] == 40)
    qs = {q['sourceRef']: q for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra'}
    assert qs['40.1.3']['answers'] == ['Хлеб.']  # not an arbitrary ban on aspectual se
    assert qs['40.1.7']['answers'] == ['На письма.']
    assert qs['40.1.10']['answers'] == ['se']  # usted
    assert qs['40.1.14']['answers'] == ['os']
    assert qs['40.2.3']['answers'][0] == 'Roque y tú os queréis'
    assert qs['40.2.5']['answers'][0] == 'Andrés y yo nos conocemos muy bien'
    assert qs['40.3.5']['answers'] == ['∅', '-', '—']
    assert qs['40.3.12']['answers'] == ['∅', '-', '—']
    assert all(s['check']['questions'] for s in u['sections'])
    assert Path('docs/grammar_unit_40_plan.md').exists()


def test_unit41_keeps_preposition_scope_person_and_exception_contrasts_explicit():
    u = next(u for u in load_grammar() if u['number'] == 41)
    qs = {q['sourceRef']: q for g in u['exercises'] for q in g['questions'] if q['sourceRef'] != 'extra'}
    assert [len(g['questions']) for g in u['exercises']] == [6, 11, 10, 8]
    assert qs['41.1.3']['answers'] == ['contigo']
    assert 'con ___' not in qs['41.1.3']['prompt']
    assert qs['41.1.4']['answers'] == ['vosotras']
    assert qs['41.1.7']['answers'] == ['nosotras']
    assert qs['41.1.6']['answers'] == ['usted']
    assert qs['41.2.3']['answers'] == ['él']  # absent Carmona, not addressed usted
    assert qs['41.2.5']['answers'] == ['ellos']
    assert qs['41.2.6']['answers'] == ['nosotros']
    assert qs['41.4.7']['answers'] == ['mí']
    assert qs['41.4.8']['answers'] == ['yo']
    assert qs['41.3.7']['answers'] == ['contigo']
    assert 'con ___' not in qs['41.3.7']['prompt']
    assert Path('docs/grammar_unit_41_plan.md').exists()
