import hashlib
import json
from pathlib import Path
from espanol.grammar import load_grammar


def test_unit20_covers_each_source_question_and_keeps_short_exercises():
    u=next(u for u in load_grammar() if u['number']==20)
    assert u['number']==20 and u['id']=='020_todos_algunos_ninguno'
    assert [len(g['questions']) for g in u['exercises']]==[8,7,6,9]
    for g,count in zip(u['exercises'],[8,7,6,5]):
        refs={q['sourceRef'] for q in g['questions'] if q['sourceRef']!='extra'}
        assert refs=={f"{g['id']}.{i}" for i in range(1,count+1)}
        assert len(g['questions'])<=15
        assert g['theorySections']
        for q in g['questions']:
            assert q['context'] and q['explain'] and q['answers']
            assert ''.join(q['inputChars'])=='áéíóúüñ'
    assert len(u['sections'])==5
    assert all(len(s['check']['questions'])==2 for s in u['sections'])


def test_quantity_tasks_and_alternatives_are_explicit():
    u=next(u for u in load_grammar() if u['number']==20);qs=u['exercises'][0]['questions']
    assert [int(q['facts']['items'][1][1]) for q in qs]==[5,3,2,1,8,1,0,3]
    assert qs[1]['answers']==['algunas cajas','unas cajas']
    assert qs[6]['answers']==['ninguna pera']
    assert u['exercises'][1]['questions'][2]['answers']==['algún','un']
    assert 'de este parque' in u['exercises'][1]['questions'][6]['prompt']
    assert u['exercises'][2]['questions'][2]['answers']==['ninguna de']
    assert u['exercises'][3]['questions'][0]['answers']==['algunos todos','unos todos']
    assert u['exercises'][3]['questions'][1]['answers']==['todos']
    assert u['exercises'][3]['questions'][2]['answers']==['ninguno']
    assert u['exercises'][3]['questions'][3]['answers']==['ninguna']


def test_existing_nineteen_units_remain_byte_identical():
    baseline=json.loads(Path('tests/data/grammar_before_unit20.json').read_text())
    assert len(baseline)==19
    for name,digest in baseline.items():
        # Git checks out CRLF on Windows; compare repository-normalized bytes.
        assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()==digest
