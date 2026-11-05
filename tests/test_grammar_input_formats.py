"""Every typing route has an explicit format, including saved word-bank attempts."""
import json

import pytest

from espanol.grammar import load_grammar


def test_all_typing_questions_have_complete_format_guidance():
    units = load_grammar()
    assert len(units) == 17
    typed = legacy = 0
    for unit in units:
        for group in [s['check'] for s in unit['sections'] if s.get('check')] + unit['exercises']:
            for q in group['questions']:
                if q.get('options'):
                    continue
                format = q.get('inputFormat', group.get('inputFormat'))
                assert format and all(format.get(k, '').strip() for k in ('instruction', 'example', 'placeholder')), (unit['number'], group['id'], q['prompt'])
                if q.get('tiles') or q.get('guidedGaps'):
                    legacy += 1
                else:
                    typed += 1
    assert (typed, legacy) == (180, 49)


@pytest.mark.parametrize('format', [{}, {'instruction':'Впиши слово'}, 'слово',
                                    {'instruction':'Впиши слово','example':'','placeholder':'Ответ'}])
def test_rejects_incomplete_format_guidance(tmp_path, format):
    fixture = {'id':'fixture','sections':[],'exercises':[{
        'id':'a','inputFormat':format,'questions':[{'prompt':'___','answers':['casa'],'explain':'Дом.'}]}]}
    (tmp_path/'001.json').write_text(json.dumps(fixture),encoding='utf8')
    with pytest.raises(ValueError, match='input format'):
        load_grammar(tmp_path)
