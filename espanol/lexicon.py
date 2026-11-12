"""Словарь изученных форм и проверка уроков.

Главное правило курса: в каждом посте используются только слова, которые
уже были введены раньше (или вводятся в этом же посте). Лексикон знает,
какие формы слов «открыты» к каждому уроку: формы из словаря урока, формы,
показанные в таблицах спряжения, и формы, которые ученик может образовать
по уже пройденным правилам (множественное число, спряжение и т. д.).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from . import morphology as morph
from .course import Course, Lesson, VocabItem
from .markup import checkable, plain
from .tokens import mixed_script_words, normalize_phrase, spanish_words

# Служебные слова не считаются «повторением» глагола или фразы.
_FUNCTION_WORDS = {
    "me", "te", "se", "nos", "os", "el", "la", "los", "las", "un", "una", "de", "a", "en", "y",
}

_PRESENT_FEATURE = {
    "regular_ar": "present_ar",
    "regular_er_ir": "present_er_ir",
    "stem": "present_stem",
}


def generated_forms(item: VocabItem, features: frozenset[str] | set[str]) -> set[str]:
    """Формы слова, которые ученик может образовать по пройденным правилам."""
    out: set[str] = set()
    if item.pos == "noun" and "plural" in features:
        if item.plural_override:
            out.update(spanish_words(item.plural_override))
        else:
            for core in item.cores:
                out.update(spanish_words(morph.plural(core)))
    elif item.pos == "adj" and "plural" in features:
        if item.plural_override:
            out.update(spanish_words(item.plural_override))
        for core in item.cores:
            for form in morph.adjective_forms(core):
                out.add(morph.plural(form))
    elif item.pos == "verb":
        for inf in item.cores:
            info = morph.verb_info(inf)
            feature = _PRESENT_FEATURE.get(morph.present_group(inf, info))
            if feature in features:
                out.update(morph.present(inf, info))
            if "reflexive" in features:
                out.update(morph.reflexive_infinitives(inf))
            if "gerund" in features:
                out.add(morph.gerund(inf, info))
            if "participle" in features:
                out.add(morph.participle(inf, info))
            if ("preterite_irregular" if morph.is_preterite_irregular(inf) else "preterite") in features:
                out.update(morph.preterite(inf, info))
            if "imperfect" in features:
                out.update(morph.imperfect(inf))
            if "imperative" in features:
                out.update(morph.imperative(inf, info))
    return {f.lower() for f in out}


def conjugation_forms(lesson: Lesson) -> set[str]:
    """Формы из таблиц спряжения: показали в уроке — значит, ввели."""
    out = set()
    for block in lesson.blocks:
        if block.type == "conjugation":
            out.update(f.lower() for f in block.data["forms"])
            out.add(block.data["verb"].lower())
    return out


def lesson_texts(lesson: Lesson, include_unit_title: bool = False) -> list[tuple[str, str]]:
    """Все тексты урока, которые увидит ученик: (где, текст)."""
    out: list[tuple[str, str]] = [("заголовок", lesson.title)]
    if include_unit_title:
        out.append(("название темы", lesson.unit.title))
        out.extend(("цели темы", g) for g in lesson.unit.goals)
    for item in lesson.vocab:
        out.append(("слово", item.es))
        out.append(("перевод слова", item.ru))
        if item.pron:
            out.append(("произношение", item.pron))
        if item.note:
            out.append(("примечание к слову", item.note))
        if item.example:
            out.append(("пример к слову", item.example.es))
            out.append(("перевод примера", item.example.ru))
    for block in lesson.blocks:
        d, where = block.data, f"блок {block.type}"
        if block.type == "words":
            continue
        if isinstance(d, str):
            out.append((where, d))
        elif block.type in ("cando", "list"):
            out.extend((where, s) for s in d)
        elif block.type == "examples":
            for ex in d["items"]:
                out += [(where, ex.es), (where, ex.ru)]
            if d.get("title"):
                out.append((where, d["title"]))
        elif block.type == "table":
            out.extend((where, cell) for row in d["rows"] for cell in row)
            if d.get("title"):
                out.append((where, d["title"]))
        elif block.type == "conjugation":
            out.extend((where, s) for s in (d.get("title"), d.get("ru")) if s)
            out.extend((where, person) for person in morph.PERSONS)
            if morph.split_verb(d["verb"])[3]:
                out.append((where, " ".join(morph.REFLEXIVE_PRONOUNS)))
        elif block.type == "exercise":
            if d.get("title"):
                out.append((where, d["title"]))
            for q, a in d["items"]:
                out.append((where, q))
                if a:
                    out.append((where, a))
        elif block.type == "dialogue":
            if d.get("title"):
                out.append((where, d["title"]))
            for speaker, es, ru in d["lines"]:
                out += [(where, speaker), (where, es), (where, ru)]
        elif block.type == "reading":
            out += [(where, d.get("title") or ""), (where, d["text"]), (where, d["translation"])]
        elif block.type == "compare":
            out += [(where, d.get(k) or "") for k in ("title", "lead", "note")]
            for c in d["cards"]:
                out += [(where, c["head"]), (where, c["label"]), (where, c["text"])]
                out += [(where, s) for pair in c["ex"] for s in pair]
        elif block.type in SCENARIO_TEXTS:
            out += [(where, t) for t in SCENARIO_TEXTS[block.type](d)]
    for n, q in enumerate(lesson.quiz, 1):
        where = f"тест, вопрос {n}"
        out += [(where, q.question), (where, q.options[q.correct]), (where, q.explain)]
    return [(w, t) for w, t in out if t]


def _mistake_notes(it) -> list[str]:
    return list(((it.get("meta") or {}).get("mistakes") or {}).values())


def _choose_texts(d) -> list[str]:
    out = [d["title"]]
    for it in d["items"]:
        out += [it["q"], it["options"][0] if it["options"] else "", it["explain"], it["say"], *_mistake_notes(it)]
        out += [t for line in it["lines"] for t in line]
        if na := it.get("noaudio"):
            out += [na["q"], na["options"][0], na["explain"]]
    return out


def _write_texts(d) -> list[str]:
    out = [d["title"]]
    for it in d["items"]:
        out += [it["q"], *it["answers"], it["explain"], it["say"], *_mistake_notes(it)]
        if na := it.get("noaudio"):
            out += [na["q"], *na["answers"], na["explain"]]
    return out


def _compose_item_texts(it) -> list[str]:
    out = [it["q"], it["format"], it["sample"], it["sample_ru"], it["explain"]]
    for c in it["checks"]:
        out += [c["label"], *c["any"], *c["all"], *c["starts"], *c["if"]]
    return out


def _chat_texts(d) -> list[str]:
    out = [d["title"], d["who"]]
    for it in d["items"]:
        out += [*it["line"], it["task"], it["explain"], *_mistake_notes(it)]
        if it["kind"] == "build":
            out += [it["es"], it["ru"], *it["alt"]]
        elif it["kind"] == "write":
            out += [*it["answers"], it["format"]]
        elif it["kind"] == "choose":
            out += it["options"][:1]
        else:
            out += _compose_item_texts(it)
    out += [t for line in d["end"] for t in line]
    return out


# Тексты блоков сценария урока сайта, которые видит ученик (кроме неверных вариантов — см. lesson_distractors).
SCENARIO_TEXTS = {
    "choose": _choose_texts,
    "write": _write_texts,
    "match": lambda d: [d["title"]] + [t for pair in d["pairs"] for t in pair],
    "sort": lambda d: [d["title"]] + [t for name, items in d["groups"] for t in (name, *items)],
    "build": lambda d: [d["title"]] + [t for it in d["items"] for t in (it["es"], it["ru"], *it["alt"])],
    "mission": lambda d: [d["title"], d["text"]],
    "more": lambda d: [d["title"], d["text"]],
    "recap": lambda d: [d["title"], d["phrase"]],
    "review": lambda d: [d["title"]],
    "compose": lambda d: [d["title"]] + [t for it in d["items"] for t in _compose_item_texts(it)],
    "chat": _chat_texts,
}


def lesson_distractors(lesson: Lesson) -> list[tuple[str, str]]:
    """Неверные варианты заданий сайта: в них можно нарочно писать ошибки (`lápizes`),
    но нельзя слова, которые вводятся позже: такой вариант отбрасывается без знания темы."""
    out = []
    for block in lesson.blocks:
        if block.type == "choose":
            out += [(f"блок choose, неверный вариант", o) for it in block.data["items"] for o in it["options"][1:]]
        elif block.type == "build":
            out += [(f"блок build, лишняя плитка", x) for it in block.data["items"] for x in it["extra"]]
        if block.type == "chat":
            for it in block.data["items"]:
                if it["kind"] == "choose":
                    out += [("блок chat, неверный вариант", o) for o in it["options"][1:]]
                if it["kind"] == "build":
                    out += [("блок chat, лишняя плитка", x) for x in it["extra"]]
                out += [("блок chat, ожидаемая ошибка", k) for k in ((it.get("meta") or {}).get("mistakes") or {})]
        if block.type in ("choose", "write"):
            # ожидаемые ошибки ученика («el cafe por favor») пишутся нарочно неверно, как неверные варианты
            out += [(f"блок {block.type}, ожидаемая ошибка", k) for it in block.data["items"]
                    for k in ((it.get("meta") or {}).get("mistakes") or {})]
            out += [(f"блок choose, неверный вариант без звука", o) for it in block.data["items"]
                    if block.type == "choose" and it.get("noaudio") for o in it["noaudio"]["options"][1:]]
    return out


@dataclass
class Issue:
    lesson: Lesson
    message: str

    def __str__(self) -> str:
        return f"Урок {self.lesson.number} ({self.lesson.id}): {self.message}"


class Lexicon:
    def __init__(self, course: Course):
        self.course = course
        self.known_at: list[frozenset[str]] = []
        self.features_at: list[frozenset[str]] = []
        self.first_seen: dict[str, Lesson] = {}
        self.names = set(course.names)
        self.items = course.items
        self._build()

    def _build(self) -> None:
        known: set[str] = set()
        features: set[str] = set()
        items: list[VocabItem] = []
        for lesson in self.course.lessons:
            before = set(known)
            new_features = set(lesson.unlocks) - features
            features |= new_features
            if new_features:
                for item in items:
                    known |= generated_forms(item, new_features)
            for item in lesson.vocab:
                items.append(item)
                known |= item.base_forms()
                known |= generated_forms(item, features)
            known |= set(lesson.forms)
            known |= conjugation_forms(lesson)
            for form in known - before:
                self.first_seen[form] = lesson
            self.known_at.append(frozenset(known))
            self.features_at.append(frozenset(features))

    # ------------------------------------------------------------ проверки

    def is_known(self, word: str, lesson: Lesson) -> bool:
        if word in self.names:
            return True
        low = word.lower()
        return (
            low in self.known_at[lesson.index]
            or low in self.course.meta_words
            or low in {a.lower() for a in lesson.allow}
        )

    def unknown_words(self, text: str, lesson: Lesson) -> list[str]:
        return [w for w in spanish_words(checkable(text)) if not self.is_known(w, lesson)]

    def check_lesson(self, lesson: Lesson) -> list[Issue]:
        issues: list[Issue] = []
        first_in_unit = lesson.unit.lessons[0] is lesson
        unknown: dict[str, str] = {}
        for where, text in lesson_texts(lesson, include_unit_title=first_in_unit):
            for word in self.unknown_words(text, lesson):
                unknown.setdefault(word, f"{where}: «{plain(text)[:60]}»")
            for word in mixed_script_words(text):
                issues.append(Issue(lesson, f"смешаны латиница и кириллица в слове «{word}» ({where})"))
        for word, where in unknown.items():
            later = self.first_seen.get(word.lower())
            hint = f" (вводится позже: урок {later.number})" if later else ""
            issues.append(Issue(lesson, f"незнакомое слово «{word}»{hint} — {where}"))
        for where, text in lesson_distractors(lesson):
            for word in self.unknown_words(text, lesson):
                later = self.first_seen.get(word.lower())
                if later and later.index > lesson.index:
                    issues.append(Issue(lesson, f"слово «{word}» вводится позже (урок {later.number}) — {where}: «{plain(text)[:60]}»"))
        return issues

    def check(self) -> list[Issue]:
        issues: list[Issue] = []
        seen: dict[str, Lesson] = {}
        max_new = self.course.settings.get("max_new_words", 8)
        for lesson in self.course.lessons:
            issues += self.check_lesson(lesson)
            if len(lesson.vocab) > max_new:
                issues.append(Issue(lesson, f"слишком много новых слов: {len(lesson.vocab)} "
                                            f"(не больше {max_new} — идём маленькими шагами)"))
            for item in lesson.vocab:
                if item.key in seen:
                    issues.append(Issue(lesson, f"слово «{item.es}» уже вводилось в уроке {seen[item.key].number}"))
                seen.setdefault(item.key, lesson)
            if lesson.kind == "quiz" and not lesson.quiz and lesson.auto_quiz == 0:
                issues.append(Issue(lesson, "в тесте нет вопросов"))
        return issues

    # ------------------------------------------------------------ повторения

    @lru_cache(maxsize=None)
    def _match_forms(self, item_index: int, features: frozenset[str]) -> tuple[frozenset[str], tuple[str, ...]]:
        """(одиночные формы, фразы) — по ним ищем слово в тексте урока."""
        item = self.items[item_index]
        singles: set[str] = set()
        phrases: list[str] = []
        for core in item.cores:
            if item.pos in ("phrase",) or len(core.split()) > 1:
                phrases.append(normalize_phrase(core))
                if item.pos == "noun" and "plural" in features:
                    phrases.append(normalize_phrase(item.plural_override or morph.plural(core)))
            elif item.pos == "adj":
                singles.update(f.lower() for f in morph.adjective_forms(core))
            else:
                singles.add(core.lower())
        singles |= generated_forms(item, features)
        if item.pos == "verb":
            singles.update(f.lower() for f in item.extra_forms)
        singles -= _FUNCTION_WORDS
        return frozenset(singles), tuple(p for p in phrases if p.strip())

    def exposures(self, lesson: Lesson, items_before: list[int]) -> set[int]:
        """Какие из ранее изученных слов встречаются в тексте урока."""
        texts = [checkable(t) for _, t in lesson_texts(lesson)]
        tokens = {w.lower() for t in texts for w in spanish_words(t)}
        phrase_text = " ".join(normalize_phrase(t) for t in texts)
        features = self.features_at[lesson.index]
        found = set()
        for idx in items_before:
            singles, phrases = self._match_forms(idx, features)
            if singles & tokens or any(p in phrase_text for p in phrases):
                found.add(idx)
        return found
