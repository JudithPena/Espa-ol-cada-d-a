import json
from pathlib import Path
from espanol.grammar import load_grammar


def test_new_possessive_units_preserve_each_source_task_and_add_targeted_corrections():
    units = [u for u in load_grammar() if u["number"] in [18,19]]
    assert [u['number'] for u in units] == [18, 19]
    for u, source_counts, totals in zip(units, [[10,8,10],[8,10,8]], [[10,8,14],[8,10,12]]):
        assert [len(g['questions']) for g in u['exercises']] == totals
        for g, count in zip(u['exercises'], source_counts):
            assert {q['sourceRef'] for q in g['questions'] if q['sourceRef'] != 'extra'} == {f"{g['id']}.{i}" for i in range(1,count+1)}
            for q in g['questions']:
                assert q['context'] and q['explain']
                assert ''.join(q['inputChars']) == 'áéíóúüñ'
        assert len(u['sections']) == 4
        assert u['learningOrder'][-1] == 'summary'
        assert all(len(s['check']['questions']) == 2 for s in u['sections'])


def test_possessive_context_and_normative_alternatives():
    a,b = [u for u in load_grammar() if u["number"] in [18,19]]
    family = a['exercises'][0]
    assert family['questions'][5]['answers'] == ['su']
    assert 'жене Begoña' in family['questions'][5]['context']
    assert 'Carmelo' in str(family['vocabulary'])
    assert a['exercises'][2]['questions'][7]['answers'] == ['la','tu']
    assert a['exercises'][2]['questions'][9]['answers'] == ['el','su']
    for qi in [3,4,5,6]:
        assert len(b['exercises'][2]['questions'][qi]['answers']) == 2
    assert b['exercises'][2]['questions'][-1]['answers'] == ['la de Ana']


def test_old_unit_files_remain_byte_identical_to_pre_possessive_baseline():
    # Snapshots cover answers/theory; this baseline protects all previous lesson content.
    baseline=json.loads(Path('tests/data/grammar_before_possessives.json').read_text())
    import hashlib
    for name,digest in baseline.items():
        assert hashlib.sha256((Path('content/grammar')/name).read_bytes()).hexdigest()==digest
