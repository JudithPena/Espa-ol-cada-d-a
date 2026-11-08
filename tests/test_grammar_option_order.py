"""An intentional teaching order needs an explicit, explained opt-out."""
import json

import pytest

from espanol.grammar import load_grammar


@pytest.mark.parametrize('where', ['group', 'question'])
@pytest.mark.parametrize('value', ['false', 0, None, [], {}])
def test_shuffle_flag_is_boolean(tmp_path, where, value):
    q = {'prompt': '___', 'answers': ['a'], 'options': ['a', 'b'], 'explain': 'a'}
    group = {'id': 'a', 'questions': [q]}
    (group if where == 'group' else q)['shuffleOptions'] = value
    (tmp_path / '001.json').write_text(json.dumps({'id': 'fixture', 'sections': [], 'exercises': [group]}))
    with pytest.raises(ValueError, match='shuffleOptions'):
        load_grammar(tmp_path)


@pytest.mark.parametrize('where', ['group', 'question'])
def test_fixed_option_order_requires_reason(tmp_path, where):
    q = {'prompt': '___', 'answers': ['a'], 'options': ['a', 'b'], 'explain': 'a'}
    group = {'id': 'a', 'questions': [q]}
    target = group if where == 'group' else q
    target['shuffleOptions'] = False
    unit = {'id': 'fixture', 'sections': [], 'exercises': [group]}
    path = tmp_path / '001.json'
    path.write_text(json.dumps(unit))
    with pytest.raises(ValueError, match='optionOrderReason'):
        load_grammar(tmp_path)
    target['optionOrderReason'] = 'Шкала от меньшего к большему'
    path.write_text(json.dumps(unit))
    loaded = load_grammar(tmp_path)[0]['exercises'][0]
    assert (loaded if where == 'group' else loaded['questions'][0])['shuffleOptions'] is False
