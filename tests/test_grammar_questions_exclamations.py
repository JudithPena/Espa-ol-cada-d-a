"""Source coverage and immutable previous lessons for units 30 onward."""
import hashlib
import json
from pathlib import Path
import pytest
from espanol.grammar import load_grammar

COUNTS = {30: {1:11, 2:11, 3:11}, 31: {1:8, 2:12, 3:12}, 32: {1:8, 2:10, 3:7, 4:5}, 33: {1:5, 2:10, 3:12}}


@pytest.mark.parametrize('number', COUNTS)
def test_source_coverage_formats_and_previous_lessons(number):
    before = json.loads(Path(f'tests/data/grammar_before_unit{number}.json').read_text())
    assert len(before) == number - 1
    for name, digest in before.items():
        assert hashlib.sha256((Path('content/grammar')/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() == digest
    u = next(u for u in load_grammar() if u['number'] == number)
    questions = [q for g in u['exercises'] for q in g['questions']]
    expected = {f'{number}.{g}.{i}' for g, count in COUNTS[number].items() for i in range(1,count+1)}
    assert {q['sourceRef'] for q in questions if q['sourceRef'] != 'extra'} == expected
    for g in u['exercises']:
        assert g['theorySections']
        for q in g['questions']:
            f = q.get('inputFormat',g['inputFormat'])
            assert f['instruction'] and f['placeholder']
            assert f.get('example') not in q['answers']
            assert ''.join(q['inputChars']) == 'áéíóúüñ'


def test_unit30_distinguishes_people_actions_number_and_personal_a():
    u = next(u for u in load_grammar() if u['number'] == 30)
    qs = {q['sourceRef']:q for g in u['exercises'] for q in g['questions']}
    assert qs['30.1.9']['answers'] == ['Qué quiere María']
    assert qs['30.1.10']['answers'] == ['Quién quiere a María']
    assert qs['30.2.9']['answers'] == ['quién','quiénes']
    assert qs['30.3.7']['answers'] == ['Quiénes']
    assert qs['30.3.9']['answers'] == ['A quién']


def test_unit31_preserves_regional_norm_and_does_not_require_geography_answers():
    u = next(u for u in load_grammar() if u['number'] == 31)
    qs = {q['sourceRef']:q for g in u['exercises'] for q in g['questions']}
    assert qs['31.2.4']['answers'] == ['Qué','Cuáles']
    assert qs['31.2.12']['answers'] == ['Qué','Cuál']
    assert qs['31.3.7']['answers'] == ['qué','cuáles']
    assert qs['31.3.8']['answers'] == ['cuál de']
    assert 'de esta historia' in qs['31.3.10']['prompt']
    assert qs['31.3.9']['interaction'] == 'build'


def test_unit32_preserves_time_location_agreement_and_interview_intention():
    u = next(u for u in load_grammar() if u['number'] == 32)
    qs = {q['sourceRef']:q for g in u['exercises'] for q in g['questions']}
    assert qs['32.2.2']['answers'] == ['Adónde','A dónde','Dónde']
    assert qs['32.2.8']['prompt'] == '¿___ no pudiste venir anoche?'
    assert qs['32.3.3']['answers'] == ['Para qué','Por qué']
    assert qs['32.4.3']['answers'] == ['Cuántas']
    assert qs['32.4.5']['answers'] == ['Cuánta']
    assert 'мужчины и женщины' in qs['32.1.7']['context']


def test_unit33_preserves_intensity_alternatives_and_illustrated_gap_formats():
    u = next(u for u in load_grammar() if u['number'] == 33)
    qs = {q['sourceRef']:q for g in u['exercises'] for q in g['questions']}
    for i in range(1,6):
        assert qs[f'33.1.{i}']['image'].startswith('data:image/webp;base64,')
        assert qs[f'33.1.{i}']['imageAlt']
    for i in [2,3,4]:
        assert qs[f'33.1.{i}']['gapWordCounts'] == [1,1]
        assert qs[f'33.1.{i}']['answers'] == ['Qué tan','Qué más']
    assert qs['33.2.5']['gapParts'] == ['¡',' barbaridad! ¡',' cuesta ese cuadro!']
    assert qs['33.2.5']['answers'] == ['Qué Cuánto']
    for ref in ['33.2.1','33.2.4','33.2.6','33.2.8','33.3.9']:
        assert set(qs[ref]['answers']) == {'Cómo','Cuánto'}
    assert qs['33.3.4']['answers'] == ['Qué cansadas']
    assert qs['33.3.11']['answers'] == ['Cuánta']
