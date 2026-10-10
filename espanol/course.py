"""Модель курса и загрузка контента из YAML-файлов.

Структура контента:
    content/course.yaml        — общие настройки, имена, географические названия
    content/units/NN_*.yaml    — темы (юниты) по порядку, в каждой список уроков

Слова в уроке можно записывать компактной строкой:
    "👋 hola [о́ла] — привет :: ¡Hola, Ana! — Привет, Анна! {pos: word}"
     эмодзи, слово, [произношение] — перевод :: пример — перевод примера {опции}
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import morphology as morph
from .tokens import spanish_words

# kind → (эмодзи, подпись, хештег)
KINDS: dict[str, tuple[str, str, str]] = {
    "intro": ("👋", "Старт", "старт"),
    "phonetics": ("🗣", "Произношение", "произношение"),
    "vocab": ("📚", "Лексика", "лексика"),
    "grammar": ("📐", "Грамматика", "грамматика"),
    "dialogue": ("💬", "Диалог", "диалог"),
    "listening": ("🎧", "Аудирование", "аудирование"),
    "reading": ("📖", "Чтение", "чтение"),
    "practice": ("✍️", "Практика", "практика"),
    "quiz": ("🧠", "Тест", "тест"),
    "review": ("🔁", "Повторение", "повторение"),
    "culture": ("🌍", "Культура", "культура"),
    "final": ("🎓", "Финал", "финал"),
}
AUDIO_KINDS = {"phonetics", "vocab", "dialogue", "listening", "reading"}

ARTICLES = {"el": "m", "la": "f", "los": "m", "las": "f", "un": "m", "una": "f", "el/la": "mf"}
POS_VALUES = {"noun", "verb", "adj", "phrase", "word", "num"}

# Грамматические темы, после которых валидатор «знает» производные формы.
FEATURES = {
    "plural": "множественное число существительных и прилагательных",
    "present_ar": "настоящее время правильных глаголов на -ar",
    "present_er_ir": "настоящее время правильных глаголов на -er/-ir",
    "present_stem": "настоящее время глаголов с чередованием в корне",
    "reflexive": "возвратные глаголы (инфинитив с местоимением)",
    "gerund": "герундий (estar + gerundio)",
    "participle": "причастие (pretérito perfecto)",
}

BLOCK_TYPES = {
    "text", "words", "rule", "tip", "note", "latam", "culture", "task", "header",
    "examples", "table", "conjugation", "exercise", "dialogue", "reading", "cando", "list",
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "srs": {
        "intervals": [1, 3, 7, 14, 30, 60, 120],
        "recall_size": 4,
        "review_size": 16,
        "review_quiz": 4,
        "quiz_auto": 4,
    },
    "max_polls": 8,
    "max_new_words": 8,  # маленькие шаги: не больше стольких новых слов за пост
}


class ContentError(Exception):
    pass


@dataclass
class Example:
    es: str
    ru: str


@dataclass
class VocabItem:
    es: str
    ru: str
    pos: str
    cores: list[str]
    emoji: str = ""
    pron: str = ""
    note: str = ""
    example: Example | None = None
    extra_forms: list[str] = field(default_factory=list)
    plural_override: str | None = None
    gender: str | None = None
    srs: bool = True
    lesson: "Lesson | None" = field(default=None, repr=False)

    @property
    def key(self) -> str:
        return self.es.lower()

    @property
    def speech(self) -> str:
        """Как произносить слово при озвучке: «alto/a» → «alto, alta»."""
        parts = []
        for variant in self.es.split(" / "):
            text = variant.replace("...", "").replace("…", "").strip()
            if text.startswith("el/la "):
                rest = text[len("el/la "):]
                parts.append(f"el {rest}, la {rest}")
                continue
            parts.append(" ".join(
                ", ".join(morph.adjective_forms(w)) if re.search(r"\w/\w", w) else w
                for w in text.split()
            ))
        return ", ".join(parts)

    def base_forms(self) -> set[str]:
        """Формы, которые ученик видит в момент знакомства со словом."""
        forms = {w.lower() for w in spanish_words(self.es)}
        for core in self.cores:
            if self.pos == "adj":
                forms.update(f.lower() for f in morph.adjective_forms(core))
            elif self.pos == "verb":
                base, _, _, reflexive = morph.split_verb(core)
                forms.add(core)
                if reflexive:
                    forms.add(base)
        forms.update(f.lower() for f in self.extra_forms)
        return forms


@dataclass
class Block:
    type: str
    data: Any


@dataclass
class QuizItem:
    question: str
    options: list[str]
    correct: int
    explain: str = ""
    shuffle: bool = True


@dataclass
class Lesson:
    id: str
    local_id: str
    kind: str
    title: str
    vocab: list[VocabItem]
    blocks: list[Block]
    quiz: list[QuizItem]
    forms: list[str]
    unlocks: list[str]
    allow: list[str]
    audio: bool
    auto_quiz: int | None
    recall: int | None
    level: str
    unit: "Unit" = field(repr=False)
    index: int = 0

    @property
    def number(self) -> int:
        return self.index + 1

    @property
    def kind_emoji(self) -> str:
        return KINDS[self.kind][0]

    @property
    def kind_label(self) -> str:
        return KINDS[self.kind][1]

    @property
    def kind_tag(self) -> str:
        return KINDS[self.kind][2]


@dataclass
class Unit:
    id: str
    number: int
    level: str
    title: str
    goals: list[str]
    lessons: list[Lesson] = field(default_factory=list)
    source: str = ""


@dataclass
class Course:
    title: str
    channel: str
    units: list[Unit]
    lessons: list[Lesson]
    names: dict[str, str]  # имя → пол (f/m/"")
    meta_words: set[str]
    settings: dict[str, Any]

    @property
    def items(self) -> list[VocabItem]:
        return [item for lesson in self.lessons for item in lesson.vocab]

    def lesson(self, ref: str | int) -> Lesson:
        """Урок по номеру (с 1) или по id вида «saludos/vocab»."""
        if isinstance(ref, int) or str(ref).isdigit():
            n = int(ref)
            if not 1 <= n <= len(self.lessons):
                raise KeyError(f"нет урока №{n} (всего {len(self.lessons)})")
            return self.lessons[n - 1]
        for lesson in self.lessons:
            if lesson.id == ref:
                return lesson
        raise KeyError(f"нет урока «{ref}»")

    def gender_of(self, speaker: str) -> str:
        return self.names.get(speaker, "")


# ---------------------------------------------------------------- парсинг


def split_pair(text: str, where: str, sep: str = " — ") -> tuple[str, str]:
    left, found, right = str(text).partition(sep)
    if not found:
        raise ContentError(f"{where}: ожидалось «испанский{sep}русский»: {text!r}")
    return left.strip(), right.strip()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return value.replace(",", " ").split()
    return [str(v) for v in value]


_HAS_LETTER = re.compile(r"[A-Za-zА-Яа-яЁёÁÉÍÓÚÜÑáéíóúüñ¿¡]")
_PRON = re.compile(r"\s*\[([^\]]+)\]\s*$")


def parse_vocab_line(line: str, where: str) -> dict:
    """Разбирает компактную запись слова в словарь полей."""
    s = line.strip()
    opts: dict = {}
    if s.endswith("}") and " {" in s:
        cut = s.rfind(" {")
        try:
            opts = yaml.safe_load(s[cut + 1:]) or {}
        except yaml.YAMLError as exc:
            raise ContentError(f"{where}: ошибка в опциях {s[cut + 1:]!r}: {exc}") from exc
        s = s[:cut].rstrip()
    example = None
    if " :: " in s:
        s, example = (part.strip() for part in s.split(" :: ", 1))
    first, _, rest = s.partition(" ")
    emoji = ""
    if rest and not _HAS_LETTER.search(first.replace("️", "").replace("⃣", "")[:1] or "x"):
        emoji, s = first, rest
    elif rest and first and not _HAS_LETTER.search(first):
        emoji, s = first, rest
    es, ru = split_pair(s, where)
    pron = ""
    m = _PRON.search(es)
    if m:
        pron, es = m.group(1), es[: m.start()]
    return {"es": es.strip(), "ru": ru, "emoji": emoji, "pron": pron, "ex": example, **opts}


def infer_pos(es: str) -> tuple[str, str | None, list[str]]:
    """Часть речи, род и «ядра» слова (без артиклей)."""
    pos, genders, cores = None, [], []
    for variant in es.split(" / "):
        clean = variant.replace("...", " ").replace("…", " ")
        clean = clean.strip(" ¿?¡!.,")
        words = clean.split()
        if not words:
            continue
        first = words[0].lower()
        if len(words) >= 2 and first in ARTICLES:
            pos = pos or "noun"
            genders.append(ARTICLES[first])
            cores.append(" ".join(words[1:]))
        elif len(words) == 1 and morph.is_verb(first):
            pos = pos or "verb"
            cores.append(first)
        elif len(words) == 1 and re.search(r"\w/\w", words[0]):
            pos = pos or "adj"
            cores.append(words[0])
        else:
            pos = pos or ("phrase" if len(words) > 1 else "word")
            cores.append(clean)
    gender = "".join(sorted(set("".join(genders)), reverse=True)) or None
    return pos or "word", gender, cores


def parse_vocab(raw: Any, where: str) -> VocabItem:
    data = parse_vocab_line(raw, where) if isinstance(raw, str) else dict(raw)
    if "es" not in data or "ru" not in data:
        raise ContentError(f"{where}: у слова должны быть поля es и ru: {raw!r}")
    es, ru = str(data["es"]).strip(), str(data["ru"]).strip()
    pos, gender, cores = infer_pos(es)
    if data.get("pos"):
        pos = str(data["pos"])
        if pos not in POS_VALUES:
            raise ContentError(f"{where}: неизвестная часть речи {pos!r} у {es!r}")
    ex = data.get("ex") or data.get("example")
    example = None
    if isinstance(ex, dict):
        example = Example(str(ex["es"]).strip(), str(ex["ru"]).strip())
    elif ex:
        example = Example(*split_pair(ex, f"{where}, пример к {es!r}"))
    return VocabItem(
        es=es,
        ru=ru,
        pos=pos,
        cores=cores,
        emoji=str(data.get("emoji") or ""),
        pron=str(data.get("pron") or ""),
        note=str(data.get("note") or ""),
        example=example,
        extra_forms=_as_list(data.get("forms")),
        plural_override=data.get("pl"),
        gender=gender,
        srs=bool(data.get("srs", True)),
    )


def _items(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def parse_block(raw: Any, where: str) -> Block:
    if isinstance(raw, str):
        return Block("text", raw)
    if not isinstance(raw, dict) or not raw:
        raise ContentError(f"{where}: непонятный блок {raw!r}")
    if "type" in raw:
        btype = raw["type"]
        value = {k: v for k, v in raw.items() if k != "type"}
    elif len(raw) == 1:
        btype, value = next(iter(raw.items()))
    else:
        raise ContentError(f"{where}: блок должен иметь один ключ-тип: {list(raw)}")
    if btype not in BLOCK_TYPES:
        raise ContentError(f"{where}: неизвестный тип блока {btype!r}")
    w = f"{where}, блок {btype}"

    if btype in ("text", "rule", "tip", "note", "latam", "culture", "task", "header"):
        return Block(btype, str(value).strip())
    if btype == "words":
        return Block(btype, None)
    if btype in ("cando", "list"):
        return Block(btype, [str(v) for v in _items(value)])
    if btype == "examples":
        spec = value if isinstance(value, dict) else {"items": value}
        items = []
        for it in _items(spec.get("items")):
            if isinstance(it, dict):
                items.append(Example(str(it["es"]).strip(), str(it["ru"]).strip()))
            else:
                items.append(Example(*split_pair(it, w)))
        return Block(btype, {"title": spec.get("title"), "items": items, "hide": spec.get("hide")})
    if btype == "table":
        spec = value if isinstance(value, dict) else {"rows": value}
        rows = [[str(c) for c in row] for row in _items(spec.get("rows"))]
        return Block(btype, {"title": spec.get("title"), "rows": rows})
    if btype == "conjugation":
        spec = value if isinstance(value, dict) else {"verb": value}
        verb = str(spec["verb"])
        forms = _as_list(spec.get("forms")) or morph.present(verb)
        if len(forms) != 6:
            raise ContentError(f"{w}: нужно 6 форм глагола {verb}")
        return Block(btype, {
            "verb": verb, "forms": forms, "title": spec.get("title"),
            "ru": spec.get("ru"), "highlight": spec.get("highlight", True),
        })
    if btype == "exercise":
        spec = value if isinstance(value, dict) else {"items": value}
        items = []
        for it in _items(spec.get("items")):
            if isinstance(it, dict):
                items.append((str(it["q"]).strip(), str(it.get("a", "")).strip() or None))
            else:
                q, found, a = str(it).partition(" => ")
                items.append((q.strip(), a.strip() if found else None))
        return Block(btype, {"title": spec.get("title"), "items": items})
    if btype == "dialogue":
        spec = value if isinstance(value, dict) else {"lines": value}
        lines = []
        for line in _items(spec.get("lines")):
            speaker, found, rest = str(line).partition(": ")
            if not found:
                raise ContentError(f"{w}: реплика должна начинаться с «Имя: »: {line!r}")
            es, _, ru = rest.partition(" | ")
            lines.append((speaker.strip(), es.strip(), ru.strip()))
        return Block(btype, {
            "title": spec.get("title"), "lines": lines, "voices": spec.get("voices") or {},
            "hidden": bool(spec.get("hidden")),  # аудирование: текст под спойлером
        })
    if btype == "reading":
        if not isinstance(value, dict) or "text" not in value:
            raise ContentError(f"{w}: нужен ключ text")
        return Block(btype, {
            "title": value.get("title"),
            "text": str(value["text"]).strip(),
            "translation": str(value.get("translation") or "").strip(),
        })
    raise ContentError(f"{w}: не обработан")  # pragma: no cover


def parse_quiz(raw: Any, where: str) -> QuizItem:
    if not isinstance(raw, dict) or "q" not in raw or "options" not in raw:
        raise ContentError(f"{where}: вопрос теста должен иметь поля q и options")
    raw_options = raw["options"]
    if isinstance(raw_options, str):  # «верный | неверный | неверный»
        raw_options = raw_options.split(" | ")
    options = [str(o).strip() for o in raw_options]
    if "answer" in raw:
        correct, shuffle = int(raw["answer"]), False
    else:
        correct, shuffle = 0, True
    if not 0 <= correct < len(options):
        raise ContentError(f"{where}: answer вне диапазона")
    return QuizItem(
        question=str(raw["q"]).strip(),
        options=options,
        correct=correct,
        explain=str(raw.get("explain") or "").strip(),
        shuffle=shuffle,
    )


def parse_lesson(raw: dict, unit: Unit, where: str) -> Lesson:
    if "id" not in raw or "kind" not in raw:
        raise ContentError(f"{where}: у урока должны быть id и kind")
    local_id, kind = str(raw["id"]), str(raw["kind"])
    where = f"{where} [{local_id}]"
    if kind not in KINDS:
        raise ContentError(f"{where}: неизвестный kind {kind!r}")
    unlocks = _as_list(raw.get("unlocks"))
    for feature in unlocks:
        if feature not in FEATURES:
            raise ContentError(f"{where}: неизвестная тема в unlocks: {feature!r}")
    lesson = Lesson(
        id=f"{unit.id}/{local_id}",
        local_id=local_id,
        kind=kind,
        title=str(raw.get("title") or KINDS[kind][1]).strip(),
        vocab=[parse_vocab(v, where) for v in _items(raw.get("vocab"))],
        blocks=[parse_block(b, where) for b in _items(raw.get("blocks"))],
        quiz=[parse_quiz(q, f"{where}, тест") for q in _items(raw.get("quiz"))],
        forms=[f.lower() for f in _as_list(raw.get("forms"))],
        unlocks=unlocks,
        allow=_as_list(raw.get("allow")),
        audio=bool(raw.get("audio", kind in AUDIO_KINDS)),
        auto_quiz=raw.get("auto_quiz"),
        recall=raw.get("recall"),
        level=str(raw.get("level") or unit.level),
        unit=unit,
    )
    for item in lesson.vocab:
        item.lesson = lesson
    return lesson


def load_course(content_dir: str | Path) -> Course:
    content_dir = Path(content_dir)
    meta = yaml.safe_load((content_dir / "course.yaml").read_text(encoding="utf-8")) or {}
    settings = {**DEFAULT_SETTINGS, **(meta.get("settings") or {})}
    settings["srs"] = {**DEFAULT_SETTINGS["srs"], **(settings.get("srs") or {})}

    names: dict[str, str] = {}
    for gender, key in (("f", "female"), ("m", "male")):
        for name in meta.get("names", {}).get(key, []) or []:
            names[str(name)] = gender
    for name, gender in (meta.get("roles") or {}).items():
        names[str(name)] = str(gender)
    for place in meta.get("places", []) or []:
        names.setdefault(str(place), "")

    units: list[Unit] = []
    lessons: list[Lesson] = []
    seen: set[str] = set()
    for number, path in enumerate(sorted((content_dir / "units").glob("*.yaml"))):
        where = path.name
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ContentError(f"{where}: ошибка YAML: {exc}") from exc
        unit = Unit(
            id=str(data.get("id") or path.stem),
            number=int(data.get("number", number)),
            level=str(data.get("level", "A1")),
            title=str(data.get("title", path.stem)),
            goals=[str(g) for g in data.get("goals", []) or []],
            source=str(path),
        )
        for raw in data.get("lessons", []) or []:
            lesson = parse_lesson(raw, unit, where)
            if lesson.id in seen:
                raise ContentError(f"{where}: повторяется id урока {lesson.id}")
            seen.add(lesson.id)
            lesson.index = len(lessons)
            unit.lessons.append(lesson)
            lessons.append(lesson)
        units.append(unit)

    return Course(
        title=str(meta.get("title", "Español")),
        channel=str(meta.get("channel", "")),
        units=units,
        lessons=lessons,
        names=names,
        meta_words={str(w).lower() for w in meta.get("meta_words", []) or []},
        settings=settings,
    )
