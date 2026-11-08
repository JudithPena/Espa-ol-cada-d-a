"""Source coverage and contextual answers for the sequential numeral lessons."""
import hashlib
import json
from pathlib import Path
from espanol.grammar import load_grammar


def unit(n):
    return next(u for u in load_grammar() if u['number'] == n)


def test_unit25_keeps_all_source_positions_with_specific_input_instructions():
    u=unit(25)
    assert [len(g['questions']) for g in u['exercises']]==[10,10,10,8]
    qs=[q for g in u['exercises'] for q in g['questions']]
    assert {q['sourceRef'] for q in qs}=={f'25.{g}.{i}' for g,count in [(1,20),(2,10),(3,8)] for i in range(1,count+1)}
    assert len(u['sections'][0]['table']['rows'])==30
    assert [r[0] for r in u['sections'][1]['table']['rows']]==['30','40','50','60','70','80','90']
    for g in u['exercises']:
        assert g['theorySections']
        for q in g['questions']:
            assert ''.join(q['inputChars'])=='áéíóúüñ'
            assert q.get('inputFormat',g['inputFormat']).get('example') not in q['answers']
    assert qs[0]['answers']==['veintiún']
    assert {'treinta y un','treinta y una'}<=set(qs[6]['answers'])
    assert qs[10]['answers']==['uno','primero']
    assert qs[15]['answers']==['veintiuna']
    assert 'cuarentainueve' in qs[3]['answers']
    assert qs[-8]['answers']==['cero dos']
    assert qs[-3]['answers']==['cero uno']


def test_pre_numeral_content_is_preserved():
    snapshot=json.loads(Path('tests/data/grammar_before_unit25.json').read_text())
    assert len(snapshot)==21
    for name,digest in snapshot.items():
        assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest


def test_unit26_covers_all_source_numbers_prices_contexts_and_dates():
    u=unit(26)
    assert [len(g['questions']) for g in u['exercises']]==[6,6,10,8,5]
    qs=[q for g in u['exercises'] for q in g['questions']]
    assert {q['sourceRef'] for q in qs if q['sourceRef']!='extra'}=={
        f'26.{g}.{i}' for g,count in [(1,8),(2,8),(3,8),(4,5)] for i in range(1,count+1)}
    assert len(u['sections'][0]['table']['rows'])==9
    assert u['exercises'][2]['questions'][7]['answers']==['mil cuatrocientas veintiuna']
    assert 'trescientas' in u['exercises'][3]['questions'][2]['answers']
    assert u['exercises'][3]['questions'][0]['answers']==['dos millones']
    assert 'de habitantes' in u['exercises'][3]['questions'][0]['prompt']
    assert 'En esta historia' in u['exercises'][3]['questions'][3]['prompt']
    assert [q['facts']['items'][-1][1] for q in u['exercises'][4]['questions']]==['1812','2001','1954','2008','1613']
    long=u['exercises'][1]['questions'][3]
    assert len(long['answers'])==4
    assert 'un millón doscientos treintaiún mil setecientos cincuentaiocho' in long['answers']
    for g in u['exercises']:
        assert g['theorySections']
        for q in g['questions']:
            assert ''.join(q['inputChars'])=='áéíóúüñ'
            assert q.get('inputFormat',g['inputFormat']).get('example') not in q['answers']


def test_unit27_covers_each_floor_name_and_both_quantity_and_order_gaps():
    u=unit(27)
    assert [len(g['questions']) for g in u['exercises']]==[7,13,15]
    qs=[q for g in u['exercises'] for q in g['questions']]
    expected={f'27.{g}.{i}' for g in [1,2] for i in range(1,11)}
    expected|={f'27.3.{i}' for i in [1,2,'3a','3b',4,5,6,7,8,9,10,11,12]}
    assert {q['sourceRef'] for q in qs if q['sourceRef']!='extra'}==expected
    by_ref={q['sourceRef']:q for q in qs}
    assert by_ref['27.1.4']['answers']==['tercer'] and by_ref['27.1.6']['answers']==['primer']
    assert by_ref['27.1.9']['answers']==['séptimo','sétimo']
    assert by_ref['27.1.10']['answers']==['noveno','nono']
    assert 'duodécimo' in by_ref['27.2.4']['answers']
    assert by_ref['27.3.3a']['answers']==['quince']
    assert {'once','undécimo'}<=set(by_ref['27.3.3b']['answers'])
    assert by_ref['27.3.6']['answers']==['primeras']
    assert by_ref['27.3.12']['answers']==['cuartas']
    for g in u['exercises']:
        assert len(g['questions'])<=15
        for q in g['questions']:
            assert ''.join(q['inputChars'])=='áéíóúüñ'
            assert q.get('inputFormat',g['inputFormat']).get('example') not in q['answers']


def test_each_completed_numeral_stage_is_frozen_before_the_next_one():
    for n, count in [(26,22),(27,23)]:
        d=json.loads(Path(f'tests/data/grammar_before_unit{n}.json').read_text())
        assert len(d)==count
        for name,digest in d.items():
            assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest
