"""Require every expected prerecorded phrase before a full-audio preview upload."""
import argparse
import json
from pathlib import Path

from espanol.course import load_course
from espanol.site import site_data
from espanol.site_audio import audio_texts, file_id
from espanol.videos import load_videos
from espanol.wordcards import load_cards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    directory = args.directory
    shell = json.loads((directory / 'index.html').read_text().split('const COURSE = ', 1)[1].split(';\n', 1)[0].replace('<\\/', '</'))
    common = json.loads((directory / shell['resources']['common']['url']).read_text())
    course = load_course('content/site')
    channel = load_course('content')
    data = site_data(course, load_cards('content'), videos=load_videos('content', channel))
    expected = {key: file_id(text, voice) for key, (text, voice) in audio_texts(data).items()}
    assert common['audio'] == expected, f'Incomplete audio map: {len(common["audio"])} / {len(expected)} keys'
    ids = set(expected.values())
    missing = [name for name in ids if not (directory / 'a' / f'{name}.mp3').is_file() or (directory / 'a' / f'{name}.mp3').stat().st_size < 500]
    assert not missing, f'Missing or empty MP3 files: {len(missing)}'
    files = list((directory / 'a').glob('*.mp3'))
    report = {'expected_keys': len(expected), 'recorded_keys': len(common['audio']),
              'expected_unique_mp3': len(ids), 'actual_mp3_files': len(files),
              'mp3_bytes': sum(p.stat().st_size for p in files), 'missing': missing}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
