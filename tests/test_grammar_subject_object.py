"""Source coverage, role clarity and preservation for the personal-pronoun units."""
import hashlib
import json
from pathlib import Path
from espanol.grammar import load_grammar


def test_unit34_source_positions_formats_and_previous_lessons():
    before = json.loads(Path('tests/data/grammar_before_unit34.json').read_text())
    assert len(before) == 33
    for name, digest in before.items():
        assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() == digest
    u = next(u for u in load_grammar() if u['number'] == 34)
    assert [len(g['questions']) for g in u['exercises']] == [10,6,3,5,4]
    qs = [q for g in u['exercises'] for q in g['questions']]
    assert {q['sourceRef'] for q in qs if q['sourceRef'] != 'extra'} == {f'34.{g}.{i}' for g,n in [(1,10),(2,4),(3,5),(4,7)] for i in range(1,n+1)}
    for g in u['exercises']:
        assert len(g['questions']) <= 15 and g['theorySections']
        for q in g['questions']:
            f=q.get('inputFormat',g['inputFormat'])
            assert f['instruction'] and f['placeholder']
            assert f.get('example') not in q['answers']
            assert ''.join(q['inputChars']) == 'áéíóúüñ'


def test_unit34_distinguishes_people_and_avoids_false_omission_rules():
    u=next(u for u in load_grammar() if u['number']==34)
    qs={q['sourceRef']:q for g in u['exercises'] for q in g['questions']}
    assert qs['34.1.2']['answers']==['Nosotros']
    assert qs['34.1.6']['answers']==['Nosotras']
    assert qs['34.1.8']['answers']==['Tú']
    assert qs['34.2.1']['answers']==['В Латинской Америке и некоторых областях Испании']
    assert qs['34.3.1']['gapWordCounts']==[1,1,1]
    assert qs['34.3.2']['answers']==['Ella él']
    assert 'тоже грамматически правильно' in qs['34.3.3']['explain']
    assert 'необязательно' in qs['34.4.6']['explain']
    assert u['sections'][0]['illustration']['image'].startswith('data:image/webp;base64,')


def test_unit35_source_positions_formats_and_previous_lessons():
    before=json.loads(Path('tests/data/grammar_before_unit35.json').read_text())
    assert len(before)==34
    for name,digest in before.items():
        assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest
    u=next(u for u in load_grammar() if u['number']==35)
    assert [len(g['questions']) for g in u['exercises']]==[8,10,12,7]
    qs=[q for g in u['exercises'] for q in g['questions']]
    assert {q['sourceRef'] for q in qs if q['sourceRef']!='extra'}=={f'35.{g}.{i}' for g,n in [(1,8),(2,8),(3,10),(4,6)] for i in range(1,n+1)}
    for g in u['exercises']:
        assert len(g['questions'])<=15 and g['theorySections']
        for q in g['questions']:
            f=q.get('inputFormat',g['inputFormat'])
            assert f['instruction'] and f['placeholder']
            assert f.get('example') not in q['answers']
            assert ''.join(q['inputChars'])=='áéíóúüñ'


def test_unit35_accepts_current_personal_leismo_without_extending_it_to_things():
    u=next(u for u in load_grammar() if u['number']==35)
    qs={q['sourceRef']:q for g in u['exercises'] for q in g['questions'] if q['sourceRef']!='extra'}
    for ref,a in [('35.1.1','le'),('35.1.3','les'),('35.1.6','les'),('35.2.4','le'),('35.2.5','les'),('35.3.7','les veo'),('35.4.5','les a ustedes'),('35.4.6','les a ellos')]:
        assert a in qs[ref]['answers']
        assert qs[ref]['answerWarnings'][a]['source']=='https://www.rae.es/dpd/le%C3%ADsmo'
    assert qs['35.1.4']['answers']==['lo']
    assert qs['35.1.5']['answers']==['la']
    assert qs['35.3.3']['answers']==['no lo he comprado']
    assert qs['35.3.4']['answers']==['os quiero']
    assert qs['35.3.8']['answers']==['no me quiere']
    assert qs['35.3.10']['answers']==['me conocen']
    assert all(qs[f'35.4.{i}']['gapWordCounts']==[1,2] for i in range(1,7))
    assert qs['35.4.2']['answers']==['nos a nosotros']
    assert u['sections'][0]['illustration']['image'].startswith('data:image/webp;base64,')
