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
import re
from pathlib import Path

from .course import FEATURES, Block, Course, Lesson, QuizItem, VocabItem
from .lexicon import _FUNCTION_WORDS, generated_forms
from .markup import plain, to_html
from .tokens import spanish_words
from .wordcards import WordCard

TEMPLATE = Path(__file__).with_name("site_template.html")

# Вводный урок рассказывает о канале: как выходят посты, где комментировать. На сайте он не нужен.
SKIP_KINDS = {"intro"}

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


# Выбор транскрипции («Как читается queso? кэ́со | куэ́со») на сайте не задаём: произношение
# проверяем на слух. В канале эти задания остаются.
_TRANSCRIPTION = re.compile(r"\s*\[[^\]]+\]\s*(?:—\s*)?")
_LATIN = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]")


def without_transcription(answer: str | None) -> str | None:
    """Ответ упражнения без транскрипции: «[ла пла́θа] — площадь» → «площадь».

    Если в ответе была одна транскрипция («el queso => [эль кэ́со]»), то ответа не остаётся: None.
    """
    if not answer:
        return answer
    m = _TRANSCRIPTION.match(answer)
    return answer if not m else (answer[m.end():].strip() or None)


def is_transcription_quiz(quiz: QuizItem) -> bool:
    """«Как читается «vino»?» с вариантами без латиницы: би́но | ви́но | фи́но."""
    return "читается" in quiz.question.lower() and not any(_LATIN.search(plain(o)) for o in quiz.options)


# «Где ударение?»: если в слове есть значок ударения (café, música), ответ виден и спрашивать нечего.
_SYLLABLES = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:-[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)+")
_ACCENT = re.compile(r"[áéíóú]", re.I)


def is_visible_stress_quiz(quiz: QuizItem) -> bool:
    """«Где ударение в слове «café»?» — значок ´ уже показывает ответ."""
    word = re.search(r"«([^»]+)»", quiz.question)
    return "ударени" in quiz.question.lower() and bool(word and _ACCENT.search(word.group(1)))


def stress_options(answer: str) -> list[str] | None:
    """Ответ «ho-TEL» → варианты с ударением на каждом слоге: [«HO-tel», «ho-TEL»].

    Так вопрос проверяет правило: соседние ответы («CA-sa», «TA-xi») выдали бы слово по буквам.
    """
    if not _SYLLABLES.fullmatch(answer) or answer == answer.lower():
        return None
    syllables = answer.lower().split("-")
    return ["-".join(x.upper() if k == n else x for k, x in enumerate(syllables)) for n in range(len(syllables))]


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
        items = []
        for q, raw in d["items"]:
            a = without_transcription(raw)
            if raw and not a:
                continue
            item = {"q": _html(q), "a": _html(a), "qp": plain(q), "ap": plain(a or "")}
            options = stress_options(item["ap"])
            if options:
                if _ACCENT.search(item["qp"]):
                    continue  # «el café => ca-FÉ»: значок ´ уже показывает ответ
                item["opts"] = options
            items.append(item)
        return {"t": t, "title": _html(d["title"]), "items": items} if items else None
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
                  "shuffle": q.shuffle, "explain": _html(q.explain)}
                 for q in lesson.quiz if not is_transcription_quiz(q) and not is_visible_stress_quiz(q)],
        "sentences": _sentences(lesson),
    }


def word_forms(course: Course) -> dict[str, str]:
    """Форма слова → слово курса (es): по нажатию на «tengo» страница покажет «tener».

    Сначала слова из одного слова (существительное без артикля, глагол, прилагательное), потом
    фразы: «buenos» из «buenos días» не перебьёт отдельное слово. Артикли и предлоги
    из чужих фраз не берём: «la» не должно открывать «la casa».
    """
    single, phrases = [], []
    for item in course.items:
        (single if all(len(core.split()) == 1 for core in item.cores) else phrases).append(item)
    verbs = {core.lower(): item for item in course.items if item.pos == "verb" for core in item.cores}
    forms: dict[str, str] = {}
    for item in single + phrases:
        own = {w.lower() for core in item.cores for w in spanish_words(core)} if item in single else set()
        found = item.base_forms() | generated_forms(item, set(FEATURES)) | {f.lower() for f in item.extra_forms}
        for form in sorted(found):
            if form in own or form not in _FUNCTION_WORDS:
                forms.setdefault(form, plain(item.es))
    for lesson in course.lessons:  # формы из таблиц спряжения
        for block in lesson.blocks:
            verb = verbs.get(block.data["verb"].lower()) if block.type == "conjugation" else None
            if verb:
                for form in block.data["forms"]:
                    for word in spanish_words(form):
                        forms.setdefault(word.lower(), plain(verb.es))
    return forms


def site_data(course: Course, cards: dict[str, WordCard], units: set[int] | None = None) -> dict:
    lessons, carried = [], []
    for lesson in course.lessons:
        if units is not None and lesson.unit.number not in units:
            continue
        data = lesson_data(lesson, cards)
        if lesson.kind in SKIP_KINDS:  # слова вводного урока переходят в следующий урок сайта
            carried += data["words"]
            continue
        data["words"] = carried + data["words"]
        carried = []
        lessons.append(data)
    return {
        "title": course.title,
        "bot": course.bot,
        "intervals": course.settings["srs"]["intervals"],
        "units": [{"number": u.number, "title": plain(u.title), "level": u.level, "goals": [plain(g) for g in u.goals]}
                  for u in course.units if units is None or u.number in units],
        "lessons": lessons,
        "forms": word_forms(course),
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
