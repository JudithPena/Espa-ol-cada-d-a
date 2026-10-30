"""Сайт курса в духе Busuu: уроки по порядку, упражнения, прогресс и повторение слов.

    python -m espanol site                    # site/index.html — открыть в браузере
    python -m espanol site --units 0-5        # только темы 0–5
    python -m espanol site --fragment         # без <html>/<head> (для встраивания)

Сайт — одна страница без сервера (шаблон espanol/site_template.html). Сюда выгружаются
уроки курса как данные: слова с карточками-разборами из content/repaso/, блоки урока в HTML,
упражнения «вопрос => ответ» и тесты. Шаги урока, варианты ответов и повторение по интервалам
собирает уже страница, а прогресс ученика хранится в его браузере (localStorage).
"""

from __future__ import annotations

import json
from pathlib import Path

from .course import Block, Course, Lesson, VocabItem
from .markup import plain, to_html
from .wordcards import WordCard

TEMPLATE = Path(__file__).with_name("site_template.html")

# Фразы для упражнения «Соберите фразу»: столько слов, не больше и не меньше.
BUILD_MIN, BUILD_MAX = 3, 8


def _html(text: str | None) -> str:
    """Мини-разметка → HTML страницы: спойлеры Telegram становятся кнопками-подсказками."""
    if not text:
        return ""
    html = to_html(str(text)).replace("\n", "<br>")
    return html.replace("<tg-spoiler>", '<span class="spoiler" tabindex="0">').replace("</tg-spoiler>", "</span>")


def _word(item: VocabItem, card: WordCard | None) -> dict:
    data = {
        "es": plain(item.es), "ru": plain(item.ru), "pron": item.pron, "emoji": item.emoji,
        "pos": item.pos, "say": item.speech, "srs": item.srs,
    }
    if item.note:
        data["note"] = _html(item.note)
    examples = card.examples if card and card.examples else (
        [(item.example.es, item.example.ru)] if item.example else [])
    if examples:
        data["ex"] = [[plain(es), plain(ru)] for es, ru in examples]
    if card:
        for key, value in (("meaning", card.meaning), ("pronNote", card.pron), ("trap", card.trap)):
            if value:
                data[key] = _html(value)
        if card.collocations:
            data["coll"] = [_html(c) for c in card.collocations]
    return data


def _block(block: Block) -> dict | None:
    t, d = block.type, block.data
    if t == "words":
        return None  # новые слова страница показывает карточками в начале урока
    if t in ("text", "rule", "tip", "note", "latam", "culture", "task", "header"):
        return {"t": t, "html": _html(d)}
    if t in ("list", "cando"):
        return {"t": t, "items": [_html(x) for x in d]}
    if t == "examples":
        return {"t": t, "title": _html(d["title"]),
                "items": [[_html(ex.es), _html(ex.ru), plain(ex.es)] for ex in d["items"]]}
    if t == "table":
        return {"t": t, "title": _html(d["title"]), "rows": [[_html(c) for c in row] for row in d["rows"]]}
    if t == "conjugation":
        return {"t": t, "verb": d["verb"], "forms": d["forms"], "title": _html(d["title"]),
                "ru": _html(d["ru"])}
    if t == "dialogue":
        return {"t": t, "title": _html(d["title"]), "hidden": d["hidden"],
                "lines": [[speaker, _html(es), _html(ru), plain(es)] for speaker, es, ru in d["lines"]]}
    if t == "reading":
        return {"t": t, "title": _html(d["title"]), "html": _html(d["text"]),
                "tr": _html(d["translation"]), "say": plain(d["text"])}
    if t == "exercise":
        items = [{"q": _html(q), "a": _html(a), "qp": plain(q), "ap": plain(a or "")} for q, a in d["items"]]
        return {"t": t, "title": _html(d["title"]), "items": items}
    raise ValueError(f"блок {t} не поддерживается сайтом")  # pragma: no cover


def _sentences(lesson: Lesson) -> list[list[str]]:
    """Фразы урока с переводом для «Соберите фразу»: примеры, диалоги, примеры к словам."""
    pairs: list[tuple[str, str]] = []
    for item in lesson.vocab:
        if item.example:
            pairs.append((item.example.es, item.example.ru))
    for block in lesson.blocks:
        if block.type == "examples":
            pairs += [(ex.es, ex.ru) for ex in block.data["items"]]
        elif block.type == "dialogue":
            pairs += [(es, ru) for _, es, ru in block.data["lines"]]
    out, seen = [], set()
    for es, ru in pairs:
        es, ru = plain(es).strip(), plain(ru).strip()
        if not ru or es in seen or not BUILD_MIN <= len(es.split()) <= BUILD_MAX:
            continue
        seen.add(es)
        out.append([es, ru])
    return out


def lesson_data(lesson: Lesson, cards: dict[str, WordCard]) -> dict:
    blocks = [b for b in (_block(block) for block in lesson.blocks) if b]
    return {
        "n": lesson.number, "id": lesson.id, "unit": lesson.unit.number, "level": lesson.level,
        "kind": lesson.kind, "kindLabel": lesson.kind_label, "emoji": lesson.kind_emoji,
        "title": plain(lesson.title),
        "words": [_word(item, cards.get(item.key)) for item in lesson.vocab],
        "blocks": blocks,
        "quiz": [{"q": plain(q.question), "options": [plain(o) for o in q.options], "correct": q.correct,
                  "shuffle": q.shuffle, "explain": _html(q.explain)} for q in lesson.quiz],
        "sentences": _sentences(lesson),
    }


def site_data(course: Course, cards: dict[str, WordCard], units: set[int] | None = None) -> dict:
    lessons = [lesson for lesson in course.lessons if units is None or lesson.unit.number in units]
    return {
        "title": course.title,
        "bot": course.bot,
        "intervals": course.settings["srs"]["intervals"],
        "units": [{"number": u.number, "title": plain(u.title), "level": u.level, "goals": [plain(g) for g in u.goals]}
                  for u in course.units if units is None or u.number in units],
        "lessons": [lesson_data(lesson, cards) for lesson in lessons],
    }


def parse_units(spec: str | None) -> set[int] | None:
    """«0-5» или «0,2,4» → номера тем; пусто — весь курс."""
    if not spec:
        return None
    numbers: set[int] = set()
    for part in spec.split(","):
        start, _, end = part.strip().partition("-")
        numbers.update(range(int(start), int(end or start) + 1))
    return numbers


def build_site(course: Course, cards: dict[str, WordCard], out: str | Path, units: set[int] | None = None,
               fragment: bool = False) -> Path:
    data = json.dumps(site_data(course, cards, units), ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/{}", data)
    if not fragment:
        # <title>, <meta> и <style> из шаблона браузер сам отнесёт в <head>.
        page = ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                f"{page}\n</html>\n")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out
