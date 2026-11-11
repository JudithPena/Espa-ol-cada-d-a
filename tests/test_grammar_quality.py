"""Schema and pedagogy checks never change progress, answers or source data."""
import copy
import json
from pathlib import Path

import pytest

from espanol.grammar import load_grammar
from espanol.grammar_quality import (
    ALLOW_FILE, DIRECTORY, apply_baseline, breaking_findings, count_content,
    inspect_directory, markdown_report, pedagogical_unit, schema_validator,
    structure_unit, summarize,
)


def fixture(number=1):
    path=next(p for p in DIRECTORY.glob('[0-9]*.json') if int(p.name.split('_',1)[0])==number)
    return path.name,json.loads(path.read_text(encoding='utf-8'))


def errors(unit):
    return breaking_findings(structure_unit(unit, 'fixture.json', schema_validator()))


def test_all_existing_data_pass_schema_and_cross_field_checks():
    units=load_grammar()
    assert len(units)==len(list(DIRECTORY.glob('[0-9]*.json')))
    assert len(units)>0
    assert not breaking_findings(inspect_directory(pedagogical=False))
    assert count_content()[1] == sum(
        sum(len(g['questions']) for g in u['exercises'])+
        sum(len(s['check']['questions']) for s in u['sections'] if s.get('check'))
        for u in units
    )


@pytest.mark.parametrize('change,rule', [
    (lambda x:x.__setitem__('titel','typo'),'SCHEMA'),
    (lambda x:x.pop('title'),'SCHEMA'),
    (lambda x:x.__setitem__('level',9),'SCHEMA'),
    (lambda x:x['exercises'][0].__setitem__('theorySections',[999]),'BROKEN_THEORY_LINK'),
    (lambda x:x['exercises'][0].pop('theorySections'),'MISSING_THEORY_LINK'),
    (lambda x:x['exercises'][0].__setitem__('id',x['exercises'][1]['id']),'DUPLICATE_GROUP'),
    (lambda x:x['exercises'][0]['questions'][0].__setitem__('answers',[]),'SCHEMA'),
    (lambda x:x['exercises'][0]['questions'][0].__setitem__('answers',['incorrecto']),'UNAVAILABLE_ANSWER'),
    (lambda x:x['exercises'][0]['questions'][0].__setitem__('optoins',['el']),'SCHEMA'),
    (lambda x:x['exercises'][0]['questions'][0].__setitem__('imageAlt',''),'MISSING_IMAGE_ALT'),
    (lambda x:x['exercises'][0]['questions'][0].__setitem__('interaction','unsupported'),'SCHEMA'),
    (lambda x:x['learningOrder'].append('section:0'),'BROKEN_LEARNING_ORDER'),
])
def test_corrupted_unit_is_rejected(change,rule):
    _,unit=fixture()
    change(unit)
    assert rule in {f.rule for f in errors(unit)}


def test_gap_arity_and_build_incompatibility():
    _,u=fixture(38)
    q=next(q for g in u['exercises'] for q in g['questions'] if q.get('gapWordCounts'))
    q['gapWordCounts']=[1,1,1,1]
    assert 'GAP_ARITY' in {x.rule for x in errors(u)}
    _,u=fixture(15)
    q=next(q for g in u['exercises'] for q in g['questions'] if q.get('tiles'))
    q['tiles']=['falso']
    assert 'UNBUILDABLE_ANSWER' in {x.rule for x in errors(u)}
    _,u=fixture(17)
    q=next(q for g in u['exercises'] for q in g['questions'] if q.get('guidedGaps'))
    q['guidedGaps']['parts']=q['guidedGaps']['parts'][:-1]
    assert 'GUIDED_ARITY' in {x.rule for x in errors(u)}


def test_alternatives_are_allowed_in_real_multiple_gap_and_choice_formats():
    for number in (1,17,38,39):
        _,u=fixture(number)
        assert not errors(u)
    _,u=fixture(1)
    q=next(q for g in u['exercises'] for q in g['questions'] if len(q['answers'])>1)
    assert len(q['answers'])>1
    assert not errors(u)
    _,u=fixture(17)
    assert any(q.get('guidedGaps') and q.get('options') for g in u['exercises'] for q in g['questions'])
    assert not errors(u)


def test_new_unit_in_external_directory_can_request_strict_validation(tmp_path):
    _,unit=fixture(38)
    unit['sections'][0]['unknown_typo']=123
    (tmp_path/'001.json').write_text(json.dumps(unit,ensure_ascii=False),encoding='utf-8')
    with pytest.raises(ValueError,match='SCHEMA'):
        load_grammar(tmp_path,schema_check=True)


def test_pedagogy_warns_for_audit_control_examples_without_blocking():
    p5,u5=fixture(5)
    p7,u7=fixture(7)
    f5=pedagogical_unit(u5,p5)
    f7=pedagogical_unit(u7,p7)
    assert any(x.rule=='CONTEXT_LEAK' and x.group=='5.2' for x in f5)
    assert any(x.rule=='NEVER_CORRECT_OPTION' and x.group=='7.1' and 'Без артикля' in x.message for x in f7)
    assert all(x.severity in ('WARNING','INFO') for x in f5+f7)
    _,u=fixture(1)
    for group in u['exercises']:
        for q in group['questions']:
            q['explain']='Повтори правило.'
    assert any(x.rule=='GENERIC_EXPLANATION' for x in pedagogical_unit(u,'mock.json'))


def test_legacy_baseline_never_hides_new_errors(tmp_path):
    _,unit=fixture()
    unit['exercises'][0]['questions'][0]['optoins']=['le']
    old=errors(unit)[0]
    assert old.severity=='ERROR'
    (tmp_path/'lint_allow.json').write_text(json.dumps({'knownErrors':[{'fingerprint':old.fingerprint,
        'reason':'Подтверждённая историческая ошибка; согласована на отдельную задачу.'}],
        'acceptedWarnings':[]}))
    exempt=apply_baseline([old],tmp_path)[0]
    assert exempt.baseline and not breaking_findings([exempt])
    other=copy.copy(unit)
    other['exercises'][0]['questions'][1]['optoins']=['le']
    new=[x for x in errors(other) if x.fingerprint!=old.fingerprint]
    assert new and breaking_findings(apply_baseline(new,tmp_path))


def test_summary_groups_and_human_report_remain_readable():
    findings=inspect_directory()
    totals=summarize(findings)
    assert set(totals['totals'])=={'ERROR','WARNING','INFO'}
    assert not totals['newErrors']
    assert any(f.rule=='SHORT_CHECK' for f in findings)
    report=markdown_report(findings,*count_content())
    assert 'Десять примеров' in report
    assert report.count('Причина:')==10
    assert len(report)<30000
    assert all(f.to_dict()['fingerprint'] for f in findings)

def test_schema_error_precedes_legacy_field_dereference(tmp_path):
    _,unit=fixture(1)
    del unit['sections']
    (tmp_path/'001_missing_sections.json').write_text(json.dumps(unit,ensure_ascii=False),encoding='utf-8')
    with pytest.raises(ValueError,match='SCHEMA'):
        load_grammar(tmp_path,schema_check=True)


def test_invalid_json_reports_error_without_counting_traceback(tmp_path,capsys):
    from types import SimpleNamespace
    from espanol.__main__ import cmd_grammar_lint
    (tmp_path/'001_invalid.json').write_text('{ not json',encoding='utf-8')
    args=SimpleNamespace(directory=str(tmp_path),unit=None,json_out=None,report=None,strict_warnings=False)
    assert cmd_grammar_lint(args,None)==1
    assert 'JSON_PARSE' in capsys.readouterr().out


def test_unknown_requested_unit_cannot_silently_pass_lint(capsys):
    from types import SimpleNamespace
    from espanol.__main__ import cmd_grammar_lint
    args=SimpleNamespace(directory=None,unit='99999',json_out=None,report=None,strict_warnings=False)
    assert cmd_grammar_lint(args,None)==2
    assert 'нет грамматических юнитов' in capsys.readouterr().out
