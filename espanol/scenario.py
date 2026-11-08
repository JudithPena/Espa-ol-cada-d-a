"""Проверки сценариев уроков сайта (content/site): порции слов, порядок и задания.

Сценарий — это список блоков урока (docs/site_lessons_guide.md). Lexicon проверяет, что в уроке только
пройденные слова, но считает все слова урока известными сразу. В сценарии слова идут порциями (`learn`),
поэтому здесь отдельно проверяем, что ни одно задание не спрашивает слово урока раньше его карточки.
"""

from __future__ import annotations

import re

from .course import GRADED_BLOCKS, SITE_ONLY_BLOCKS, Course, Lesson
from .lexicon import SCENARIO_TEXTS, Issue, Lexicon, generated_forms, lesson_texts
from .markup import checkable, plain
from .tokens import spanish_words

MAX_OPTIONS = 5
MAX_PAIRS = 6


def _key(text: str) -> str:
    """Сравнение вариантов: без регистра, разметки и знаков."""
    return re.sub(r"[\s¿¡?!.,;:«»\"'…—–-]+", " ", plain(text).lower()).strip()


def _exact(text: str) -> str:
    """Вариант выбора как его видит ученик: без регистра и лишних пробелов, но со знаками ¿ ? ¡ !."""
    return " ".join(plain(text).lower().split())


def _tile(token: str) -> str:
    """Плитка «Соберите фразу» без регистра и знаков по краям: так её сравнивает страница."""
    return re.sub(r"^[¿¡\"«]+|[.,;:!?\"»…]+$", "", token.lower())


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in spanish_words(checkable(text))]


def _graded_texts(block) -> list[str]:
    """Испанские тексты задания, по которым видно, какое слово оно проверяет (с неверными вариантами)."""
    d = block.data
    if block.type == "exercise":
        return [t for q, a in d["items"] for t in (q, a or "")]
    texts = SCENARIO_TEXTS[block.type](d)
    if block.type == "choose":
        texts += [o for it in d["items"] for o in it["options"]]
    if block.type == "build":
        texts += [x for it in d["items"] for x in it["extra"]]
    return texts


def _block_issues(lesson: Lesson, block) -> list[str]:
    d, t = block.data, block.type
    out = []
    if t == "choose":
        for it in d["items"]:
            keys = [_exact(o) for o in it["options"]]
            if not 2 <= len(keys) <= MAX_OPTIONS:
                out.append(f"choose: нужно от 2 до {MAX_OPTIONS} вариантов — {it['q'] or it['say']!r}")
            if len(set(keys)) != len(keys):
                out.append(f"choose: одинаковые варианты — {it['options']!r}")
            if not (it["q"] or it["say"] or it["lines"] or it["img"]):
                out.append("choose: у вопроса нет ни q, ни say, ни lines, ни img")
    elif t == "write":
        for it in d["items"]:
            if not it["answers"]:
                out.append(f"write: нет ответа — {it['q']!r}")
            if not (it["q"] or it["say"] or it["img"]):
                out.append("write: у задания нет ни q, ни say, ни img")
    elif t == "match":
        lefts, rights = [_key(a) for a, _ in d["pairs"]], [_key(b) for _, b in d["pairs"]]
        if not 2 <= len(lefts) <= MAX_PAIRS:
            out.append(f"match: нужно от 2 до {MAX_PAIRS} пар")
        if len(set(lefts)) != len(lefts) or len(set(rights)) != len(rights):
            out.append("match: стороны пар повторяются — пару нельзя будет выбрать однозначно")
    elif t == "sort":
        items = [_key(x) for _, xs in d["groups"] for x in xs]
        if len(d["groups"]) < 2 or any(not xs for _, xs in d["groups"]):
            out.append("sort: нужно не меньше двух непустых групп")
        if len(set(items)) != len(items):
            out.append("sort: карточка повторяется — у неё будет две верные группы")
    elif t == "build":
        for it in d["items"]:
            words = it["es"].split()
            if not 2 <= len(words) <= 10:
                out.append(f"build: во фразе нужно от 2 до 10 слов — {it['es']!r}")
            for alt in it["alt"]:
                if sorted(map(_tile, alt.split())) != sorted(map(_tile, words)):
                    out.append(f"build: другой порядок должен состоять из тех же плиток — {alt!r}")
            if {_tile(x) for x in it["extra"]} & {_tile(x) for x in words}:
                out.append(f"build: лишняя плитка совпадает со словом фразы — {it['extra']!r}")
    elif t == "learn":
        pass
    return out


def _img_issues(block) -> list[str]:
    from .site import ART, ART_SLUGS

    if block.type not in ("choose", "write"):
        return []
    bad = [it["img"] for it in block.data["items"] if it["img"] and not (it["img"] in ART_SLUGS and (ART / f"{ART_SLUGS[it['img']]}.webp").exists())]
    return [f"{block.type}: у слова «{x}» нет картинки (ART_SLUGS в espanol/site.py)" for x in bad]


def check_lesson(lesson: Lesson, lexicon: Lexicon) -> list[Issue]:
    issues = [Issue(lesson, msg) for block in lesson.blocks for msg in _block_issues(lesson, block) + _img_issues(block)]
    blocks = lesson.blocks
    for k, block in enumerate(blocks):
        if block.type == "mission" and not any(b.type in GRADED_BLOCKS for b in blocks[k + 1:]):
            issues.append(Issue(lesson, "mission: после миссии нужно хотя бы одно задание"))
        if block.type == "more" and k == 0:
            issues.append(Issue(lesson, "more: свёрнутое пояснение должно идти после блока, который оно поясняет"))
    if not lesson.scripted:
        return issues
    by_es = {item.es: item for item in lesson.vocab}
    placed: dict[str, int] = {}
    for k, block in enumerate(blocks):
        if block.type != "learn":
            continue
        for es in block.data:
            if es not in by_es:
                issues.append(Issue(lesson, f"learn: «{es}» нет среди слов урока (vocab)"))
            elif es in placed:
                issues.append(Issue(lesson, f"learn: слово «{es}» стоит в двух порциях"))
            else:
                placed[es] = k
    for item in lesson.vocab:
        if item.es not in placed:
            issues.append(Issue(lesson, f"learn: слово «{item.es}» не стоит ни в одной порции"))
    # Задание не спрашивает слово урока до его карточки. Формы, известные до урока, не в счёт:
    # «un» из прошлых уроков можно спрашивать и до карточки «un / una».
    before = lexicon.known_at[lesson.index - 1] if lesson.index else frozenset()
    features = lexicon.features_at[lesson.index]
    forms = {es: (item.base_forms() | generated_forms(item, features)) - before for es, item in by_es.items()}
    for k, block in enumerate(blocks):
        if block.type not in GRADED_BLOCKS | {"exercise"}:
            continue
        later = {es for es, at in placed.items() if at > k}
        used = {tok for text in _graded_texts(block) for tok in _tokens(text)}
        for es in sorted(later):
            hit = sorted(used & forms[es])
            if hit:
                issues.append(Issue(lesson, f"{block.type}: задание спрашивает «{hit[0]}» раньше карточки слова «{es}»"))
    return issues


def check(course: Course, lexicon: Lexicon | None = None) -> list[Issue]:
    """Проверки сценариев всех уроков сайта."""
    lexicon = lexicon or Lexicon(course)
    return [issue for lesson in course.lessons for issue in check_lesson(lesson, lexicon)]


def channel_issues(course: Course) -> list[Issue]:
    """Блоки сайта в уроках канала: канал их не покажет."""
    return [Issue(lesson, f"блок {block.type} есть только на сайте (content/site), в канале его не показать")
            for lesson in course.lessons for block in lesson.blocks if block.type in SITE_ONLY_BLOCKS]


__all__ = ["check", "check_lesson", "channel_issues", "lesson_texts"]
