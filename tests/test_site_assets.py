"""Deployment contract: identical teaching data, bounded shell, immutable assets."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from espanol.course import load_course
from espanol.site import build_site, site_data
from espanol.site_assets import Resources, split_site
from espanol.site_budget import check_budget
from espanol.wordcards import load_cards


@pytest.fixture(scope='module')
def deployed(tmp_path_factory):
    out = tmp_path_factory.mktemp('deployment')
    course, cards = load_course('content/site'), load_cards('content')
    from espanol.videos import load_videos
    videos = load_videos('content', course)
    build_site(course, cards, out / 'index.html', videos=videos)
    page = (out / 'index.html').read_text()
    shell = json.loads(page.split('const COURSE = ', 1)[1].split(';\n', 1)[0].replace('<\\/', '</'))
    return out, shell, site_data(course, cards, videos=videos)


def read(out, ref):
    path = out / ref['url']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == path.stem
    return json.loads(path.read_text())


def test_deployment_budgets_and_lazy_catalogs(deployed):
    out, shell, _ = deployed
    report = check_budget(out)
    assert report['html_bytes'] < 1_500_000
    assert set(shell['resources']['levels']) == {'A0', 'A1', 'A2'}   # A2 — с 12 ноября 2026
    assert all('blocks' not in L and 'quiz' not in L for L in shell['lessons'])
    assert all('questions' not in g for u in shell['grammar'] for g in u['exercises'])
    assert shell['books'] == []
    assert all('blocks' not in t for b in read(out, shell['resources']['books']) for t in b['chapters'] + ([b['story']] if b.get('story') else []))
    assert 'data:image' not in (out / 'index.html').read_text()
    assert 'immutable' in (out / '_headers').read_text()
    for path in (out / 'd').rglob('*.json'):
        assert 'data:image' not in path.read_text()


def test_hydration_preserves_every_field_and_answer(deployed):
    out, original_shell, full = deployed
    shell = copy.deepcopy(original_shell)
    shell['books'] = read(out, shell['resources']['books'])
    shell['lessons'] = [L for ref in shell['resources']['levels'].values() for L in read(out, ref)['lessons']]
    for u in shell['grammar']:
        data = read(out, u['_data']); u.clear(); u.update(data)
    for v in shell['videos']:
        data = read(out, v['_data']); v.clear(); v.update(data)
    for b in shell['books']:
        for text in b['chapters'] + ([b['story']] if b.get('story') else []):
            data = read(out, text['_data']); text.clear(); text.update(data)
    common = read(out, shell.pop('resources')['common'])
    shell['avatars'], shell['audio'] = common['avatars'], common['audio']
    # Same external URLs for byte-identical images (including existing g/ art).
    from espanol.grammar import write_theory_illustrations
    write_theory_illustrations(full['grammar'], out)
    expected = Resources(out).images(full)
    expected.setdefault('audio', {})
    assert shell == expected
    assert common['words'] == [L['words'] for L in shell['lessons']]


def test_books_stage_is_lossless(deployed, tmp_path):
    _, _, full = deployed
    shell = split_site(full, tmp_path, books_only=True)
    for b in shell['books']:
        for text in b['chapters'] + ([b['story']] if b.get('story') else []):
            data = read(tmp_path, text['_data']); text.clear(); text.update(data)
    assert shell == Resources(tmp_path).images(full)


def test_hashes_change_only_for_changed_resources(tmp_path):
    writer = Resources(tmp_path)
    first = writer.json('d/test', {'text': 'one'}, 'text')
    assert first == writer.json('d/test', {'text': 'one'}, 'text')
    assert first != writer.json('d/test', {'text': 'two'}, 'text')
    assert read(tmp_path, first) == {'text': 'one'}


def test_future_levels_use_same_contract(deployed, tmp_path):
    _, _, original = deployed
    sample = copy.deepcopy(original)
    sample['units'][0]['level'] = 'C2'
    shell = split_site(sample, tmp_path)
    assert 'C2' in shell['resources']['levels']
    expected_ids = [L['id'] for L in sample['lessons'] if L['unit'] == sample['units'][0]['number']]
    assert [L['id'] for L in read(tmp_path, shell['resources']['levels']['C2'])['lessons']] == expected_ids


def test_all_three_budget_limits_block_upload(tmp_path):
    (tmp_path / 'index.html').write_text('12345')
    with pytest.raises(ValueError, match='HTML'):
        check_budget(tmp_path, html_limit=4)
    with pytest.raises(ValueError, match='Asset'):
        check_budget(tmp_path, asset_limit=4)
    with pytest.raises(ValueError, match='Files'):
        check_budget(tmp_path, file_limit=0)
    assert check_budget(tmp_path)['file_count'] == 1


def test_recorded_audio_map_stays_in_common_data(deployed, tmp_path):
    _, _, original = deployed
    sample = copy.deepcopy(original)
    sample['audio'] = {'hola': 'a/existing.mp3', '@voice|hola': 'a/dialogue.mp3'}
    shell = split_site(sample, tmp_path)
    assert shell['audio'] == {}
    assert read(tmp_path, shell['resources']['common'])['audio'] == sample['audio']
