import json
from pathlib import Path

import pytest

from espanol.grammar import GRAMMAR, load_grammar


def test_every_new_theory_has_an_embedded_illustration_and_readable_examples():
    units=[u for u in load_grammar() if 4 <= u['number'] <= 14]
    sections=[s for u in units for s in u['sections']]
    assert len(sections)==39
    assert all(s['illustration']['image'].startswith('data:image/webp;base64,') for s in sections)
    assert all(s['illustration']['alt'] and s['illustration']['examples'] for s in sections)
    assert all(len(pair)==2 and all(pair) for s in sections for pair in s['illustration']['examples'])
    prompts=json.loads((GRAMMAR/'art/theory-004-014/prompts.json').read_text(encoding='utf-8'))
    assert len(prompts['images'])==39
    assert {p['file'] for p in prompts['images']}=={f"{u['number']:03}{chr(97+i)}.webp" for u in units for i in range(len(u['sections']))}


@pytest.mark.parametrize('value', [None, {}, {'image':'a.webp','alt':'Описание','examples':[['одна строка']]}])
def test_rejects_incomplete_illustration_metadata(tmp_path, value):
    u=json.loads((GRAMMAR/'004_articulo_indefinido.json').read_text(encoding='utf-8'))
    u['sections'][0]['illustration']=value if value is not None else {'image':'a.webp'}
    (tmp_path/'004.json').write_text(json.dumps(u),encoding='utf-8')
    with pytest.raises(ValueError,match='bilingual examples'):
        load_grammar(tmp_path)


def test_theory_image_cannot_escape_the_content_directory(tmp_path):
    u=json.loads((GRAMMAR/'004_articulo_indefinido.json').read_text(encoding='utf-8'))
    u['sections'][0]['illustration']['image']='../outside.webp'
    (tmp_path/'004.json').write_text(json.dumps(u),encoding='utf-8')
    with pytest.raises(ValueError,match='invalid grammar image path'):
        load_grammar(tmp_path)
