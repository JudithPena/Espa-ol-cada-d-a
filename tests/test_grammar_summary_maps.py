import copy
import json
from pathlib import Path
import pytest
from espanol.grammar import load_grammar, GRAMMAR

def test_summary_maps_keep_fallback_and_resolve_existing_illustrations():
    for u in load_grammar():
        m=u['summary'].get('topicMap')
        if u['number'] not in (60,61,62,63,64,65,71,72):
            assert m is None
            continue
        assert u['summary']['rows'] and u['summary']['heads']
        assert len(m['cards'])==6
        assert u['learningOrder'][-1]=='summary'
        for c in m['cards']:
            if 'illustrationSection' in c:
                assert u['sections'][c['illustrationSection']]['illustration']['image'].startswith('data:image/webp;base64,')

def test_map_illustration_reference_cannot_silently_point_outside_unit(tmp_path):
    u=json.loads((GRAMMAR/'060_he_trabajado.json').read_text(encoding='utf8'))
    u['summary']['topicMap']['cards'][0]['illustrationSection']=999
    (tmp_path/'060_test.json').write_text(json.dumps(u),encoding='utf8')
    with pytest.raises(ValueError,match='summary map illustrationSection'):
        load_grammar(tmp_path,schema_check=True)
