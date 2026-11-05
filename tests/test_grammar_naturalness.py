"""Conversational examples keep their referents, translations, and grammatical purpose."""
import json

import pytest

from espanol.grammar import load_grammar


def test_geography_examples_are_complete_question_answer_pairs():
    s = load_grammar()[3]['sections'][1]
    assert not s.get('wordGroups')
    colombia, sevilla, people = s['dialogues']
    assert colombia['lines'] == [['¿Colombia es una ciudad?', 'Колумбия — это город?'],
                                 ['No, es un país.', 'Нет, это страна.']]
    assert sevilla['lines'] == [['¿Sevilla es una ciudad?', 'Севилья — это город?'],
                               ['Sí, es una ciudad de España.', 'Да, это город в Испании.']]
    assert people['lines'][0][0] == '¿Quién es esa mujer?'
    assert people['lines'][1][0] == 'Es una pintora.'
    assert people['lines'][3][0] == 'Es un científico.'


def test_time_prices_and_short_answers_have_explicit_context():
    units = load_grammar()
    time = units[8]['sections'][0]['dialogues']
    assert [d['lines'][1][0] for d in time[:2]] == ['Es la una y veinte.', 'Son las tres y media.']
    assert time[2]['lines'][0][0] == '¿A qué hora empieza la película?'
    assert time[2]['lines'][1][0] == 'A la una.'
    assert time[2]['lines'][3][0] == 'A las ocho.'
    price = units[8]['sections'][3]['dialogues'][0]
    assert price['lines'][0][0] == '¿Cuánto cuestan las manzanas?'
    assert price['lines'][1] == ['Dos euros el kilo.', 'Два евро за килограмм.']
    short = units[15]['sections'][5]['dialogues']
    assert 'Luis' in short[0]['lines'][0][0]
    assert short[0]['lines'][-1][0] == 'Es igual de listo.'
    assert 'Elena' in short[1]['lines'][0][0]
    assert short[1]['lines'][-1][0] == 'No son tan elegantes.'


def test_requests_and_translations_fit_their_situation():
    units = load_grammar()
    requests = units[3]['sections'][3]['wordGroups']
    assert all('hija' not in es for g in requests for es, _ in g['words'])
    assert requests[0]['words'][0] == ['Necesito un mapa.', 'Мне нужна карта.']
    assert units[13]['sections'][2]['wordGroups'][0]['words'][0] == ['una moneda japonesa', 'японская монета']
    words = units[10]['sections'][1]['wordGroups'][0]['words']
    assert words[0][0].startswith('las galletas de chocolate')
    assert words[1][0].startswith('los zapatos de arriba')


@pytest.mark.parametrize('dialogues', [None, {}, [{}], [{'title':'', 'lines':[['Hola','Привет'],['Hola','Привет']]}],
    [{'title':'Разговор','lines':[['Hola','Привет']]}], [{'title':'Разговор','lines':[['Hola'],['Hola','Привет']]}]])
def test_malformed_dialogues_are_rejected(tmp_path, dialogues):
    u = {'id':'fixture','sections':[{'dialogues':dialogues}], 'exercises':[]}
    (tmp_path/'001.json').write_text(json.dumps(u), encoding='utf-8')
    with pytest.raises(ValueError, match='dialogue'):
        load_grammar(tmp_path)
