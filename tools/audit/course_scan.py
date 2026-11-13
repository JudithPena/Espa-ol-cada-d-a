#!/usr/bin/env python3
"""Сканеры аудита основного курса сайта (content/site): только чтение, в validate и CI не подключены.

    python tools/audit/course_scan.py inventory        # объём по темам и урокам
    python tools/audit/course_scan.py balance          # распознавание / воспроизведение / слух по урокам
    python tools/audit/course_scan.py recycle [-v] [--window N]  # слова, которые после своей темы не встречаются (в ближайших N темах)
    python tools/audit/course_scan.py distractors      # самые частые неверные варианты и «верный — самый длинный»
    python tools/audit/course_scan.py situations       # ситуационные формулировки («Вы не знаете…», «Попросите…»)
    python tools/audit/course_scan.py sources          # вопросы к диалогу / тексту вместе с источником
    python tools/audit/course_scan.py single           # ввод с единственным принятым ответом из 3+ слов
    python tools/audit/course_scan.py skills           # покрытие навыков skills.yaml заданиями
    python tools/audit/course_scan.py repeats          # одинаковые вопросы в разных уроках
    python tools/audit/course_scan.py cyrillic         # реплики и фразы на слух, где испанский смешан с кириллицей

Каждая строка вывода — сигнал для ручной проверки, а не готовая находка (docs/a0_a1_mythos_audit.md, раздел «Метод»).
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from espanol.course import load_course          # noqa: E402
from espanol.lexicon import generated_forms, lesson_texts   # noqa: E402
from espanol.markup import plain                # noqa: E402
from espanol.tokens import spanish_words        # noqa: E402

GRADED = ("choose", "write", "match", "sort", "build")
CYR = re.compile("[а-яёА-ЯЁ]")
LAT = re.compile("[a-záéíóúüñ]", re.I)


def course():
    return load_course(ROOT / "content/site")


def site_lessons(c):
    return [L for L in c.lessons if L.scripted]   # start/intro на сайте не показывается


def tasks(lesson):
    """Все оцениваемые пункты урока: (тип, блок, пункт)."""
    for b in lesson.blocks:
        if b.type in ("choose", "write", "build"):
            for it in b.data["items"]:
                yield b.type, b, it
        elif b.type in ("match", "sort"):
            yield b.type, b, None
    for q in lesson.quiz:
        yield "quiz", None, q


def kind_of(t, it):
    """Мыслительное действие пункта (грубо): recog — узнать, listen — на слух, prod — ввести, build — собрать."""
    if t == "quiz":
        return "recog"
    if t in ("match", "sort"):
        return "recog"
    if t == "choose":
        return "listen" if it.get("say") else "recog"
    if t == "write":
        return "dictation" if it.get("say") else "prod"
    return "build"


def cmd_inventory(c):
    print("тема | уровень | уроков | слов | пунктов заданий | диалогов | текстов | миссий")
    total = collections.Counter()
    for u in c.units:
        ls = [L for L in u.lessons if L.scripted]
        n = sum(1 for L in ls for _ in tasks(L))
        row = collections.Counter(b.type for L in ls for b in L.blocks)
        words = sum(len(L.vocab) for L in ls)
        print(f"{u.number:02d} {u.title} | {u.level} | {len(ls)} | {words} | {n} | {row['dialogue']} | {row['reading']} | {row['mission']}")
        total.update(lessons=len(ls), words=words, items=n, dialogue=row["dialogue"], reading=row["reading"], mission=row["mission"])
    print("итого:", dict(total))
    kinds = collections.Counter(L.kind for L in site_lessons(c))
    print("типы уроков:", dict(kinds))
    types = collections.Counter(t for L in site_lessons(c) for t, _, _ in tasks(L))
    print("пункты по типам:", dict(types))


def cmd_balance(c):
    print("урок | вид | слов | узнавание | на слух | диктант | ввод | сборка | доля воспроизведения")
    for L in site_lessons(c):
        k = collections.Counter(kind_of(t, it) for t, _, it in tasks(L))
        n = sum(k.values()) or 1
        prod = (k["prod"] + k["build"] + k["dictation"]) / n
        print(f"{L.id} | {L.kind} | {len(L.vocab)} | {k['recog']} | {k['listen']} | {k['dictation']} | {k['prod']} | {k['build']} | {prod:.0%}")


# Все грамматические возможности курса: слово «встречено» и во множественном числе, и в любой форме глагола (SYS-08).
_ALL_FEATURES = {"plural", "present_ar", "present_er_ir", "present_stem", "reflexive", "gerund", "participle", "preterite",
                 "preterite_irregular", "imperfect", "imperative", "conditional", "superlative"}


def _forms(item):
    return {f.lower() for f in item.base_forms() | generated_forms(item, _ALL_FEATURES) if len(f) > 2}


def cmd_recycle(c):
    """Слово считается встреченным, если любая его словарная форма есть в текстах более позднего урока."""
    lessons = site_lessons(c)
    texts = []
    for L in lessons:
        words = set()
        for _, t in lesson_texts(L):
            words.update(w.lower() for w in spanish_words(plain(t)))
        texts.append(words)
    by_unit = collections.defaultdict(list)
    for i, L in enumerate(lessons):
        for item in L.vocab:
            forms = _forms(item)
            if not forms:
                continue
            later_lessons = [lessons[j] for j in range(i + 1, len(lessons)) if forms & texts[j]]
            other_units = {x.unit.number for x in later_lessons if x.unit.number != L.unit.number}
            by_unit[L.unit.number].append((item.es, len(later_lessons), sorted(other_units)))
    window = int(sys.argv[sys.argv.index("--window") + 1]) if "--window" in sys.argv else None
    head = "тема | слов | не встречаются в других темах | из них ни разу после своего урока"
    print(head + (f" | не возвращаются в ближайших {window} темах" if window else ""))
    for u in sorted(by_unit):
        rows = by_unit[u]
        lonely = [r for r in rows if not r[2]]
        never = [r for r in rows if r[1] == 0]
        far = [r for r in rows if window and not any(x <= u + window for x in r[2])]
        print(f"{u:02d} | {len(rows)} | {len(lonely)} | {len(never)}" + (f" | {len(far)}" if window else ""))
        if "-v" in sys.argv:
            print("    не в других темах:", ", ".join(r[0] for r in lonely))
            if window:
                print(f"    не в ближайших {window} темах:", ", ".join(r[0] for r in far))


def cmd_distractors(c):
    wrong = collections.Counter()
    longest = total = 0
    per_lesson = collections.defaultdict(lambda: [0, 0])
    for L in site_lessons(c):
        for t, b, it in tasks(L):
            if t == "choose":
                opts = [plain(o) for o in it["options"]]
            elif t == "quiz":
                opts = [plain(it.options[it.correct])] + [plain(o) for k, o in enumerate(it.options) if k != it.correct]
            else:
                continue
            for o in opts[1:]:
                wrong[o] += 1
            if len(opts) >= 3:
                total += 1
                per_lesson[L.id][1] += 1
                if len(opts[0]) > max(len(o) for o in opts[1:]):
                    longest += 1
                    per_lesson[L.id][0] += 1
    print(f"верный вариант строго длиннее остальных: {longest} из {total} ({longest / total:.0%}; случайно было бы ~33 %)")
    print("уроки, где верный — самый длинный чаще чем в 60 % вопросов (от 4 вопросов):")
    for lid, (a, b) in per_lesson.items():
        if b >= 4 and a / b > 0.6:
            print(f"  {lid}: {a}/{b}")
    print("самые частые неверные варианты:")
    for o, n in wrong.most_common(40):
        print(f"  {n:3d}  {o}")


SITUATION = re.compile(r"Вы не знаете|Вы не расслышали|Вы хотите|Попросите|Спросите|Что (вы )?скажете|Как (вы )?ответите|Что ответить|Вам нужно|Вы не поняли", re.I)


def cmd_situations(c):
    for L in site_lessons(c):
        for t, b, it in tasks(L):
            q = it.question if t == "quiz" else (it.get("q") if it else "") or ""
            title = (b.data.get("title") or "") if b else ""
            if SITUATION.search(plain(q)) or (it is not None and t != "quiz" and SITUATION.search(plain(title)) and not q):
                extra = ""
                if t == "choose":
                    extra = " || " + " | ".join(plain(o) for o in it["options"])
                    if it.get("lines"):
                        extra = " [" + " / ".join(f"{sp}: {plain(es)}" for sp, es, _ in it["lines"]) + "]" + extra
                elif t == "write":
                    extra = " => " + " | ".join(plain(a) for a in it["answers"])
                elif t == "quiz":
                    extra = " || " + " | ".join(plain(o) for o in it.options)
                print(f"{L.id} [{t}] {plain(title)}: {plain(q)}{extra}")


def cmd_sources(c):
    for L in site_lessons(c):
        ids = {b.meta.get("id"): b for b in L.blocks if b.meta.get("id")}
        shown = set()
        for t, b, it in tasks(L):
            meta = (it.meta if t == "quiz" else {**(b.meta or {}), **((it or {}).get("meta") or {})})
            src = meta.get("source")
            if not src or src not in ids:
                continue
            sb = ids[src]
            if src not in shown:
                shown.add(src)
                print(f"\n=== {L.id} @{src} ({sb.type}) ===")
                if sb.type == "dialogue":
                    for sp, es, ru in sb.data["lines"]:
                        print(f"   {sp}: {plain(es)}")
                elif sb.type == "reading":
                    print("   " + plain(sb.data["text"]).replace("\n", " "))
                else:
                    print("   " + plain(sb.data.get("text") or ""))
            if t == "quiz":
                print(f" Q[quiz] {plain(it.question)} || " + " | ".join(plain(o) for k, o in sorted(enumerate(it.options), key=lambda p: p[0] != it.correct)))
            elif t == "choose":
                head = plain(it.get("q") or "") or ("say: " + plain(it.get("say") or "")) or ""
                if it.get("lines"):
                    head += " [" + " / ".join(f"{sp}: {plain(es)}" for sp, es, _ in it["lines"]) + "]"
                print(f" Q[choose] {head} || " + " | ".join(plain(o) for o in it["options"]))
            elif t == "write":
                print(f" Q[write] {plain(it.get('q') or '')} => " + " | ".join(plain(a) for a in it["answers"]))
            elif t == "build":
                print(f" Q[build] {plain(it['ru'])} => {plain(it['es'])}")
            else:
                print(f" Q[{t}] {plain(b.data.get('title') or '')}")


def cmd_single(c):
    n = total = 0
    for L in site_lessons(c):
        for t, b, it in tasks(L):
            if t != "write" or it.get("say"):
                continue
            total += 1
            answers = [plain(a) for a in it["answers"]]
            if len(answers) == 1 and len(answers[0].split()) >= 3:
                n += 1
                print(f"{L.id}: {plain(it.get('q') or '')} => {answers[0]}")
    print(f"\nввод без диктанта: {total}; с единственным ответом из 3+ слов: {n}")


def cmd_skills(c):
    use = collections.defaultdict(lambda: collections.Counter())
    where = collections.defaultdict(set)
    for L in site_lessons(c):
        for t, b, it in tasks(L):
            meta = (it.meta if t == "quiz" else {**(b.meta or {}), **((it or {}).get("meta") or {})})
            sk = meta.get("skill") or []
            sk = [sk] if isinstance(sk, str) else sk
            free = not meta.get("source")
            for s in sk:
                use[s]["free" if free else "source"] += 1
                use[s][kind_of(t, it)] += 1
                where[s].add(L.unit.number)
    untagged = sum(1 for L in site_lessons(c) for t, b, it in tasks(L)
                   if not ((it.meta if t == "quiz" else {**(b.meta or {}), **((it or {}).get("meta") or {})}).get("skill")))
    print(f"навыков в skills.yaml: {len(c.skills)}; пунктов без навыка: {untagged}")
    print("навык | урок введения | самост. | к источнику | узнавание | ввод+сборка | темы")
    for s, info in c.skills.items():
        u = use[s]
        print(f"{s} | {info.get('lesson')} | {u['free']} | {u['source']} | {u['recog'] + u['listen']} | {u['prod'] + u['build'] + u['dictation']} | {sorted(where[s])}")


def cmd_repeats(c):
    seen = collections.defaultdict(list)
    for L in site_lessons(c):
        for t, b, it in tasks(L):
            if t == "quiz":
                key = (plain(it.question), plain(it.options[it.correct]))
            elif t == "choose":
                key = (plain(it.get("q") or it.get("say") or "") + " ".join(plain(es) for _, es, _ in (it.get("lines") or [])), plain(it["options"][0]))
            elif t == "write":
                key = (plain(it.get("q") or it.get("say") or ""), plain(it["answers"][0]))
            elif t == "build":
                key = ("build", plain(it["es"]))
            else:
                continue
            seen[key].append(L.id)
    n = 0
    for key, ids in seen.items():
        if len(ids) > 1:
            n += 1
            print(f"{len(ids)}× {key[0]!r} → {key[1]!r}: {', '.join(ids)}")
    print(f"\nповторяющихся пунктов: {n}")


def cmd_cyrillic(c):
    for L in site_lessons(c):
        for b in L.blocks:
            if b.type == "dialogue":
                for sp, es, ru in b.data["lines"]:
                    if CYR.search(plain(es)) and LAT.search(plain(es)):
                        print(f"{L.id} диалог: {sp}: {plain(es)}")
        for t, b, it in tasks(L):
            if t in ("choose", "write") and it.get("say") and CYR.search(plain(it["say"])):
                print(f"{L.id} на слух: {plain(it['say'])}")
            if t == "choose":
                for sp, es, _ in it.get("lines") or []:
                    if CYR.search(plain(es)) and LAT.search(plain(es)):
                        print(f"{L.id} реплика задания: {sp}: {plain(es)}")


COMMANDS = {k[4:]: v for k, v in globals().items() if k.startswith("cmd_")}

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[name](course())
