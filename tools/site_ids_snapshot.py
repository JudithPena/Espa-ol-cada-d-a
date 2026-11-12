#!/usr/bin/env python3
"""Снимок id уроков сайта (tests/data/site_lesson_ids.json): по id хранится прогресс учеников.

    python tools/site_ids_snapshot.py        — дописать в конец новые уроки (новые темы уровня)

Менять или переставлять уже записанные id нельзя: инструмент только дописывает и падает, если прежний
порядок не совпал с курсом.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from espanol.course import load_course  # noqa: E402

path = ROOT / "tests" / "data" / "site_lesson_ids.json"
old = json.loads(path.read_text(encoding="utf-8"))
ids = [lesson.id for lesson in load_course(ROOT / "content" / "site").lessons]
if ids[:len(old)] != old:
    sys.exit("id или порядок прежних уроков изменились — снимок не обновлён")
path.write_text("[\n" + ",\n".join(json.dumps(i, ensure_ascii=False) for i in ids) + "\n]\n", encoding="utf-8")
print(f"уроков в снимке: {len(old)} → {len(ids)}")
