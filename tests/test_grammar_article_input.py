"""Article production keeps course identity, a gradual introduction and explicit omission."""
import json
from pathlib import Path
import pytest
from espanol.grammar import load_grammar


def test_article_input_audit_keeps_a_mixed_progression_and_all_question_answers():
    units = load_grammar()
    changes = json.loads(Path('docs/grammar_article_input_changes.json').read_text())
    audit = json.loads(Path('docs/grammar_article_input_audit.json').read_text())
    assert [u['unit'] for u in audit['units']] == list(range(1, 18))
    assert sum(len(u['exercises']) for u in audit['units']) == 60
    assert changes['convertedChoices'] == 173
    for change in changes['questions']:
        # 2026 Fable stage 4 intentionally changed unit 7; the November 8 audit is historical.
        if change['unit'] in (5, 7):
            continue
        unit = units[change['unit'] - 1]
        group = next(g for g in unit['exercises'] if g['id'] == change['group'])
        q = group['questions'][change['question'] - 1]
        for key in ('prompt', 'answers', 'explain', 'translation', 'sourceRef', 'answerWarnings'):
            assert q.get(key) == change['before'].get(key), (group['id'], key)
        assert not q.get('options') and q['interaction'] == 'article-input'
        assert 'example' not in q['inputFormat']
    family = units[5]['exercises'][1]
    assert len(family['questions']) == 8
    assert all(q['interaction'] == 'article-input' for q in family['questions'])
    assert family['questions'][0]['translation'] == 'Отца Марты зовут Фелипе.'
    for n, gid in [(6, '6.2'), (6, '6.3'), (11, '11.2')]:
        group = next(g for g in units[n - 1]['exercises'] if g['id'] == gid)
        assert group['preview']['source'] not in [q['prompt'] for q in group['questions']]
    for n, gid in [(2, '2.1'), (4, '4.1'), (6, '6.1')]:
        group = next(g for g in units[n - 1]['exercises'] if g['id'] == gid)
        assert group['questions'][0].get('options')
        assert any(q.get('interaction') == 'article-input' for q in group['questions'])
    for u in units:
        for g in u['exercises']:
            if any('Без артикля' in q['answers'] and not q.get('options') for q in g['questions']):
                assert g.get('allowNoArticle'), g['id']


@pytest.mark.parametrize('kind', ['options', 'wrong_word', 'missing_omission', 'bad_flag'])
def test_invalid_article_input_configuration_is_rejected(tmp_path, kind):
    q = {'prompt': '___ libro', 'answers': ['el'], 'explain': 'el libro', 'interaction': 'article-input'}
    g = {'id': 'a', 'questions': [q]}
    if kind == 'options': q['options'] = ['el', 'la']
    elif kind == 'wrong_word': q['answers'] = ['libro']
    elif kind == 'missing_omission': q['answers'] = ['Без артикля']
    else: g['allowNoArticle'] = 'true'
    (tmp_path / '001.json').write_text(json.dumps({'id': 'fixture', 'sections': [], 'exercises': [g]}))
    with pytest.raises(ValueError, match='article-input|allowNoArticle'):
        load_grammar(tmp_path)
