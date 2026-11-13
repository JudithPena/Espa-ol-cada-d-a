#!/usr/bin/env python3
"""Список известных предупреждений о содержании заданий сайта (content/site/lint_baseline.json).

    python tools/lint_baseline.py          — записать текущие предупреждения (после правки урока, когда
                                             предупреждение снято; новые предупреждения сюда не добавляйте —
                                             их исправляют в уроке)
    python tools/lint_baseline.py --add    — дописать и новые (только для сознательно оставленных случаев)

Проверки — espanol/content_lint.py (аудит MYTHOS, этап 4). Тест test_no_new_content_warnings падает и на новом
предупреждении, и на устаревшей строке списка.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from espanol.content_lint import BASELINE, baseline, warnings, write_baseline  # noqa: E402
from espanol.course import load_course  # noqa: E402
from espanol.lexicon import Lexicon  # noqa: E402

site = load_course(ROOT / "content" / "site")
found = [key for key, _ in warnings(site, Lexicon(site))]
old = baseline()
keep = found if "--add" in sys.argv else [k for k in found if k in old]
new = [k for k in found if k not in old]
write_baseline(keep)
print(f"{BASELINE.name}: {len(old)} → {len(set(keep))}" + (f"; новых предупреждений {len(new)} — исправьте их в уроках:" if new and "--add" not in sys.argv else ""))
if "--add" not in sys.argv:
    for k in new:
        print("  ", k)
