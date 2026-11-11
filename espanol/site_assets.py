"""Static, content-addressed learning resources. Source content is never modified."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
from pathlib import Path

IMAGE = re.compile(r'data:image/(webp|png|jpeg|jpg);base64,([A-Za-z0-9+/=]+)')
LEVELS = ('A0', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2')


class Resources:
    def __init__(self, output: Path):
        self.output = output

    def write(self, folder: str, data: bytes, suffix: str) -> str:
        relative = f'{folder}/{hashlib.sha256(data).hexdigest()}.{suffix}'
        target = self.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(data)
        return relative

    def images(self, value):
        if isinstance(value, dict):
            return {k: self.images(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.images(v) for v in value]
        if isinstance(value, str):
            return IMAGE.sub(lambda m: self.write('i', base64.b64decode(m[2], validate=True),
                                                  'jpg' if m[1] == 'jpeg' else m[1]), value)
        return value

    def json(self, folder: str, value, kind: str) -> dict:
        data = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        return {'url': self.write(folder, data, 'json'), 'kind': kind}


def split_books(site: dict, resources: Resources) -> None:
    """Retain navigation metadata; each published text has an independent resource."""
    for book in site['books']:
        for chapter in book['chapters']:
            ref = resources.json(f'd/books/{book["id"]}', chapter, 'text')
            meta = {k: v for k, v in chapter.items() if k not in ('blocks', 'exercises')}
            chapter.clear()
            chapter.update(meta, _data=ref)
        if book.get('story'):
            text = book['story']
            ref = resources.json(f'd/books/{book["id"]}', text, 'text')
            book['story'] = {k: v for k, v in text.items() if k not in ('blocks', 'exercises')}
            book['story']['_data'] = ref


def split_site(site: dict, output: Path, *, books_only: bool = False) -> dict:
    """Create deployment resources from the already validated in-memory course.

    Level files are discovered from metadata, so A2–C2 require no loader changes.
    books_only is also used to measure/verify the first implementation stage.
    """
    resources = Resources(output)
    shell = resources.images(copy.deepcopy(site))
    split_books(shell, resources)
    if books_only:
        return shell
    common = {'words': [lesson['words'] for lesson in shell['lessons']],
              'avatars': shell.get('avatars', {}), 'audio': shell.get('audio', {})}
    shell['resources'] = {'common': resources.json('d/common', common, 'common'),
                          'books': resources.json('d/books-catalog', shell['books'], 'books'), 'levels': {}}
    shell['books'] = []
    shell['avatars'], shell['audio'] = {}, {}
    by_level = {}
    units = {unit['number']: unit['level'] for unit in shell['units']}
    for lesson in shell['lessons']:
        level = units[lesson['unit']]
        if level not in LEVELS:
            raise ValueError(f'Unknown course level: {level}')
        by_level.setdefault(level, []).append(copy.deepcopy(lesson))
    for level, lessons in by_level.items():
        shell['resources']['levels'][level] = resources.json(f'd/levels/{level.lower()}', {'lessons': lessons}, 'level')
    for lesson in shell['lessons']:
        lesson['_data'] = shell['resources']['levels'][units[lesson['unit']]]
        lesson['words'] = []
        for key in ('blocks', 'quiz', 'sentences'):
            lesson.pop(key)
    for unit in shell['grammar']:
        ref = resources.json(f'd/grammar/{unit["id"]}', unit, 'grammar')
        # Completion badges use only routes and group IDs, never question content.
        meta = {k: unit[k] for k in ('id', 'number', 'title', 'subtitle', 'learningOrder', 'revision') if k in unit}
        meta['sections'] = [{'check': {'id': s['check']['id']}} if s.get('check') else {} for s in unit['sections']]
        meta['exercises'] = [{'id': g['id']} for g in unit['exercises']]
        unit.clear()
        unit.update(meta, _data=ref)
    for video in shell['videos']:
        ref = resources.json(f'd/videos/{video["id"]}', video, 'video')
        meta = {k: v for k, v in video.items() if k != 'segments'}
        meta['segments'] = [None] * len(video['segments'])
        video.clear()
        video.update(meta, _data=ref)
    return shell
