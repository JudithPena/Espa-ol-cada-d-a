"""Recovery destinations must be explicit and refer to real theory, not a unit's home."""
import json

import pytest

from espanol.grammar import load_grammar


def test_every_exercise_has_a_review_block_in_learning_order():
    units = load_grammar()
    assert len(units) == 65
    assert sum(len(u['exercises']) for u in units) == 255
    for unit in units:
        for group in unit['exercises']:
            assert group['theorySections']
            for section in group['theorySections']:
                assert unit['learningOrder'].index(f'section:{section}') < unit['learningOrder'].index(f'exercise:{group["id"]}')
    plural = units[2]
    assert [g['theorySections'] for g in plural['exercises']] == [list(range(7)), [7], [8]]
    assert [g['theorySections'] for g in units[16]['exercises']] == [[0, 1, 2], [5], [3, 4], [6]]


@pytest.mark.parametrize('sections', [[], [0, 0], [1], [-1], [True], 'section:0'])
def test_invalid_theory_destinations_cannot_ship(tmp_path, sections):
    fixture = {'id':'test','sections':[{}],'exercises':[{'id':'practice','theorySections':sections,'questions':[]}]}
    (tmp_path/'001.json').write_text(json.dumps(fixture),encoding='utf8')
    with pytest.raises(ValueError, match='theorySections'):
        load_grammar(tmp_path)
