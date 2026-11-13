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
    "final": ("🎓", "Итоговый тест", "итог"),
    "finale": ("🎉", "Финиш", "финиш"),
    "video": ("🎬", "Разбор видео", "разбор_видео"),  # отдельная рубрика, см. videos.py
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
    # A2
    "preterite": "pretérito indefinido правильных глаголов (и глаголов с чередованием)",
    "preterite_irregular": "pretérito indefinido с особой основой (tuve, hice, fui, dije…)",
    "imperfect": "pretérito imperfecto",
    "imperative": "утвердительный императив (tú, usted, vosotros, ustedes)",
    "conditional": "condicional simple (me gustaría, podrías, deberías, tendría)",
    "superlative": "абсолютная степень на -ísimo (carísimo, riquísimo, facilísimo)",
}

BLOCK_TYPES = {
    "text", "words", "rule", "tip", "note", "latam", "culture", "task", "header",
    "examples", "table", "conjugation", "exercise", "dialogue", "reading", "cando", "list",
    "compare",   # только уроки сайта (content/site): карточки рядом — tú / usted, ¿…? / ¡…!
    # Только уроки сайта: сценарий урока (docs/site_lessons_guide.md). Блоки ставятся в любом порядке,
    # движок страницы показывает их по очереди: порция слов → пример → задания → ещё слова → миссия.
    "learn",     # порция новых слов урока: карточки этих слов в этом месте урока
    "choose",    # выбор ответа (первый вариант верный), на слух (say) или продолжение диалога (lines)
    "write",     # короткий ввод: слово, артикль, форма, фраза; допустимые ответы — через « | »
    "match",     # соедините пары «es — ru»
    "sort",      # распределите по группам
    "build",     # соберите фразу из плиток; alt — другие допустимые порядки, extra — лишние плитки
    "mission",   # итоговая ситуация: экран-сцена, за ним задания миссии
    "more",      # «Почему? / Подробнее»: свёрнутое пояснение на экране предыдущего блока
    "recap",     # проверка слов урока, которых не коснулись задания (и «Мастер фраз»), там, где решил автор
    "review",    # запланированное повторение навыков прошлых уроков (content/site/skills.yaml)
    "compose",   # направляемое письмо: несколько фраз от себя, проверка по признакам и образец (без «неверно»)
    "chat",      # разговор по шагам: реплика собеседника → ответ ученика (сборка, ввод, выбор, письмо)
}

# Блоки, которых в уроках канала быть не может (validate проверяет content/units).
SITE_ONLY_BLOCKS = {"compare", "learn", "choose", "write", "match", "sort", "build", "mission", "more", "recap", "review",
                    "compose", "chat"}
# Задания сценария, которые проверяет страница (у каждого — правильный ответ).
GRADED_BLOCKS = {"choose", "write", "match", "sort", "build", "compose", "chat"}
# Открытые задания: проверяются по признакам, в повторение навыков не идут.
OPEN_BLOCKS = {"compose", "chat"}
# Блоки, с которыми урок идёт по сценарию (Lesson.scripted).
SCRIPT_BLOCKS = GRADED_BLOCKS | {"learn", "mission"}
# Источники контекста: задание после них проверяет понимание (source) или самостоятельное (free).
SOURCE_BLOCKS = {"dialogue", "reading", "mission"}
# Объяснения, на которые может ссылаться «📖 Повторить правило» (rule: id).
RULE_TARGETS = {"rule", "tip", "note", "text", "compare", "table", "list", "examples", "conjugation", "more"}
# Служебные поля блока урока сайта (docs/site_lessons_guide.md): id блока, граница экрана, источник,
# правило и навык задания. В уроках канала их нет, рендер канала их не видит (Block.meta).
META_KEYS = ("id", "slide", "source", "free", "rule", "skill", "evidence")
CHECKS = ("", "control", "soft")

DEFAULT_SETTINGS: dict[str, Any] = {
    "srs": {
        "intervals": [1, 3, 7, 14, 30, 60, 120],
        "recall_size": 4,
        "recall_min": 3,
        "review_size": 16,
        "review_quiz": 4,
        "quiz_auto": 4,
    },
    "max_polls": 8,
    "max_new_words": 8,  # маленькие шаги: не больше стольких новых слов за пост
    "rich_posts": [],    # уроки, которые уходят постом-статьёй: список id или all
    "site_open_units": None,  # темы, открытые на основном сайте; None — все
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
    clue: str = ""  # загадка для викторины, если слово похоже на русское (content/clues.yaml)
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
    meta: dict = field(default_factory=dict)   # сайт: id, slide, source, free, rule, skill (META_KEYS)


@dataclass
class QuizItem:
    question: str
    options: list[str]
    correct: int
    explain: str = ""
    shuffle: bool = True
    meta: dict = field(default_factory=dict)   # сайт: source, free, skill, rule


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
    goal: str = ""   # сайт: микроцель урока — наблюдаемое действие («здоровается утром, днём и вечером»)
    version: int = 1  # сайт: версия содержания урока; прохождение старой версии не подтверждает новую
    check: str = ""   # сайт: control — итог уровня с порогом, soft — тест темы с честной оценкой
    cover_subtitle: str = ""  # канал: подпись на обложке вместо названия темы (итоги уровня относятся ко всему уровню)

    @property
    def scripted(self) -> bool:
        """Урок сайта со сценарием: слова идут порциями (learn), задания — там, где их поставил автор.
        Урок без этих блоков страница собирает прежним путём: все слова, объяснение, практика."""
        return any(b.type in SCRIPT_BLOCKS for b in self.blocks)

    @property
    def number(self) -> int:
        """Номер в канале: вводный урок — 0, дальше 1, 2, 3…"""
        return self.index

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
    bot: str = ""  # бот для повторений (без @): ссылка «Повторить слова» в конце уроков
    # Сайт: навыки-конструкции для повторения и итогов (content/site/skills.yaml): тег → {title, lesson}.
    skills: dict[str, dict] = field(default_factory=dict)

    @property
    def items(self) -> list[VocabItem]:
        return [item for lesson in self.lessons for item in lesson.vocab]

    def lesson(self, ref: str | int) -> Lesson:
        """Урок по номеру (вводный — 0) или по id вида «saludos/vocab»."""
        if isinstance(ref, int) or str(ref).isdigit():
            n = int(ref)
            if not 0 <= n < len(self.lessons):
                raise KeyError(f"нет урока №{n} (номера от 0 до {len(self.lessons) - 1})")
            return self.lessons[n]
        for lesson in self.lessons:
            if lesson.id == ref:
                return lesson
        raise KeyError(f"нет урока «{ref}»")

    def is_rich(self, lesson: Lesson) -> bool:
        """Публиковать ли урок постом-статьёй (настройка rich_posts в course.yaml)."""
        rich = self.settings.get("rich_posts") or []
        return rich in ("all", True) or lesson.id in rich

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
_OPTIONS = re.compile(r"\s(\{[^{}]*\})\s*(?=::|$)")


def parse_vocab_line(line: str, where: str) -> dict:
    """Разбирает компактную запись слова в словарь полей."""
    s = line.strip()
    opts: dict = {}
    m = _OPTIONS.search(s)  # {опции} — в конце строки или перед «::»
    if m:
        try:
            opts = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as exc:
            raise ContentError(f"{where}: ошибка в опциях {m.group(1)!r}: {exc}") from exc
        s = (s[: m.start()] + " " + s[m.end():]).strip()
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


def _text(value: Any) -> str:
    """Строка из элемента списка. YAML превращает «текст: текст» в словарь — склеиваем обратно."""
    if isinstance(value, dict):
        return "; ".join(f"{k}: {v}" for k, v in value.items())
    return str(value)


def _items(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def parse_block(raw: Any, where: str) -> Block:
    if isinstance(raw, str):
        return Block("text", raw.strip())
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
    meta: dict = {}
    if isinstance(value, dict):
        meta = _meta(value, w)
        value = {k: v for k, v in value.items() if k not in META_KEYS}
    block = _parse_block(btype, value, w)
    block.meta = {**block.meta, **meta}
    return block


def _meta(spec: dict, where: str) -> dict:
    """Служебные поля блока или вопроса сайта: id, slide: new, source: id, free: true, rule: id | none, skill."""
    meta = {k: spec[k] for k in META_KEYS if k in spec and spec[k] not in (None, "")}
    for k in ("id", "source", "rule"):
        if k in meta:
            meta[k] = str(meta[k]).strip()
    if "slide" in meta and meta["slide"] != "new":
        raise ContentError(f"{where}: slide может быть только new")
    if "free" in meta:
        meta["free"] = bool(meta["free"])
    if "skill" in meta:
        meta["skill"] = [str(x).strip() for x in _items(meta["skill"]) if str(x).strip()]
    if "evidence" in meta:   # цитата из источника, из которой следует ответ (аудит MYTHOS, TST-01)
        meta["evidence"] = [str(x).strip() for x in _items(meta["evidence"]) if str(x).strip()]
    if meta.get("source") and meta.get("free"):
        raise ContentError(f"{where}: у задания либо source, либо free")
    return meta


VARIANT_INHERIT = ("skill", "source", "free", "rule", "format", "answer")


def _with_variants(items: list, w: str) -> list:
    """Варианты задания итога (аудит MYTHOS, этап 5): «variants: [...]» у задания — равноценные замены для пересдачи.
    Разворачиваются в обычные задания блока с общей группой `vg` (все проверки видят каждый вариант), а страница
    показывает из группы одно — по номеру попытки."""
    out = []
    for g, it in enumerate(items):
        if not (isinstance(it, dict) and it.get("variants")):
            out.append(it)
            continue
        base = {k: v for k, v in it.items() if k != "variants"}
        out.append({**base, "vg": g})
        for v in _items(it["variants"]):
            if not isinstance(v, dict):
                raise ContentError(f"{w}: вариант задания — словарь с теми же полями, что у задания")
            # Вариант равноценен заданию: тот же навык и источник (их берут из задания), та же форма — на слух
            # или нет, с репликой или без; своя альтернатива без звука (noaudio не наследуется).
            for k in ("skill", "source", "free", "variants"):
                if k in v:
                    raise ContentError(f"{w}: у варианта задания не задают {k} — он берётся из самого задания")
            for k in ("say", "lines", "img"):
                if (k in base) != (k in v):
                    raise ContentError(f"{w}: вариант задания должен быть той же формы, что и задание ({k} есть у одного из них)")
            if v.get("say") and not v.get("noaudio") and base.get("noaudio"):
                raise ContentError(f"{w}: у варианта на слух нужна своя альтернатива noaudio")
            out.append({**{k: base[k] for k in VARIANT_INHERIT if k in base}, **v, "vg": g})
    return out


def _parse_block(btype: str, value: Any, w: str) -> Block:

    if btype in ("text", "rule", "tip", "note", "latam", "culture", "task", "header"):
        if isinstance(value, dict):   # сайт: {text: …, id: …, join: true}
            if "text" not in value:
                raise ContentError(f"{w}: нужен ключ text")
            block = Block(btype, str(value["text"]).strip())
            if value.get("join"):
                block.meta["join"] = True
            return block
        return Block(btype, str(value).strip())
    if btype == "words":
        return Block(btype, None)
    if btype in ("cando", "list"):
        if isinstance(value, dict):   # сайт: {items: […], id: …}
            value = value.get("items")
        return Block(btype, [_text(v) for v in _items(value)])
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
            "join": bool(spec.get("join")),      # сайт: на том же экране, что и блок перед ним
        })
    if btype == "compare":
        # cards: [{head, label, text, ex: ["es — ru"], tone}], style: big | small, title, lead, note
        if not isinstance(value, dict) or not _items(value.get("cards")):
            raise ContentError(f"{w}: нужен список cards")
        cards = []
        for c in _items(value["cards"]):
            if not isinstance(c, dict) or "head" not in c:
                raise ContentError(f"{w}: у карточки нужен head")
            ex = [tuple(p.strip() for p in str(e).partition(" — ")[::2]) for e in _items(c.get("ex"))]
            cards.append({"head": str(c["head"]).strip(), "label": str(c.get("label") or "").strip(),
                          "text": str(c.get("text") or "").strip(), "ex": ex, "tone": str(c.get("tone") or ""),
                          "say": c.get("say", True) is not False})   # say: false — шапку не озвучивать («+ -s»)
        return Block(btype, {"title": value.get("title"), "lead": value.get("lead"), "note": value.get("note"),
                             "style": value.get("style") or "big", "cards": cards,
                             "join": bool(value.get("join"))})   # join: на том же экране, что и блок перед ним
    if btype in SITE_ONLY_BLOCKS - {"compare"}:
        return _scenario_block(btype, value, w)
    if btype == "reading":
        if not isinstance(value, dict) or "text" not in value:
            raise ContentError(f"{w}: нужен ключ text")
        return Block(btype, {
            "title": value.get("title"),
            "text": str(value["text"]).strip(),
            "translation": str(value.get("translation") or "").strip(),
        })
    raise ContentError(f"{w}: не обработан")  # pragma: no cover


def _options(raw: Any) -> list[str]:
    """«верный | неверный | неверный» или список → варианты; первый — верный."""
    if isinstance(raw, str):
        raw = raw.split(" | ")
    return [str(o).strip() for o in _items(raw) if str(o).strip()]


MAX_ANSWERS = 96
ANSWER_KINDS = ("number", "time", "phone", "date")


def _expand(text: str) -> list[str]:
    """Шаблон ответа → варианты: «(Yo) vivo [en/a] Madrid» — круглые скобки — необязательная часть,
    квадратные — одно из перечисленного через «/». Вложенность допускается."""
    def seq(i: int, stop: str) -> tuple[list[str], int]:
        out = [""]
        while i < len(text) and text[i] not in stop:
            ch = text[i]
            if ch in "([":
                close = ")" if ch == "(" else "]"
                parts, i = alt(i + 1, close)
                if i >= len(text) or text[i] != close:
                    raise ContentError(f"в шаблоне ответа не закрыта скобка: {text!r}")
                i += 1
                if ch == "(":
                    parts = parts + [""]
                out = [a + b for a in out for b in parts]
            else:
                out = [a + ch for a in out]
                i += 1
            if len(out) > MAX_ANSWERS * 4:
                raise ContentError(f"шаблон ответа даёт слишком много вариантов: {text!r}")
        return out, i

    def alt(i: int, close: str) -> tuple[list[str], int]:
        parts: list[str] = []
        while True:
            got, i = seq(i, "/" + close)
            parts += got
            if i < len(text) and text[i] == "/":
                i += 1
                continue
            return parts, i

    got, i = seq(0, "")
    first = re.search(r"[^\W\d_]", text)
    upper = bool(first and first.group().isupper())
    out = []
    for g in got:
        g = re.sub(r"\s+([,.!?;:])", r"\1", " ".join(g.split()))
        g = re.sub(r"^[,;:]\s*", "", g)
        g = re.sub(r"([¿¡])\s+", r"\1", g)
        if upper:
            g = re.sub(r"[^\W\d_]", lambda m: m.group().upper(), g, count=1)
        if g and g not in out:
            out.append(g)
    return out


def _alts(raw: Any) -> list[str]:
    """Допустимые ответы: «el libro | un libro» или список. Шаблоны «(Yo) vivo [en/a] …» разворачиваются
    в варианты при сборке (docs/site_lessons_guide.md, «Шаблоны ответов»)."""
    out: list[str] = []
    for item in _options(raw):
        for v in (_expand(item) if re.search(r"[(\[]", item) else [item]):
            if v not in out:
                out.append(v)
    if len(out) > MAX_ANSWERS:
        raise ContentError(f"слишком много вариантов ответа ({len(out)}): {str(raw)[:60]!r}")
    return out


def _line(raw: Any, where: str) -> tuple[str, str, str]:
    """Реплика «Имя: испанский | перевод» (перевод можно не писать)."""
    speaker, found, rest = str(raw).partition(": ")
    if not found:
        raise ContentError(f"{where}: реплика должна начинаться с «Имя: »: {raw!r}")
    es, _, ru = rest.partition(" | ")
    return speaker.strip(), es.strip(), ru.strip()


def _item_meta(it: dict, where: str) -> dict:
    """Поля вопроса задания: source/free/rule/skill (как у блока), mistakes — пояснения к ожидаемым ошибкам."""
    meta = _meta(it, where)
    mistakes = it.get("mistakes") or {}
    if not isinstance(mistakes, dict):
        raise ContentError(f"{where}: mistakes — словарь «ошибка: пояснение»")
    meta["mistakes"] = {str(k).strip(): _text(v) for k, v in mistakes.items()}
    return meta


def _noaudio(raw: Any, btype: str, where: str) -> dict | None:
    """Альтернатива заданию на слух, если ученику нечем слушать: та же цель письменно.
    choose: {q, options, explain}; write: {q, a, explain, format}."""
    if raw in (None, "", {}):
        return None
    if not isinstance(raw, dict) or not str(raw.get("q") or "").strip():
        raise ContentError(f"{where}: noaudio — словарь с q")
    out = {"q": str(raw["q"]).strip(), "explain": str(raw.get("explain") or "").strip()}
    if btype == "choose":
        out["options"] = _options(raw.get("options"))
        if len(out["options"]) < 2:
            raise ContentError(f"{where}: у noaudio нужны options (первый — верный)")
    else:
        out["answers"] = _alts(raw.get("a"))
        out["format"] = str(raw.get("format") or "").strip()
        if not out["answers"]:
            raise ContentError(f"{where}: у noaudio нужен a")
    return out


CHECK_KEYS = ("any", "all", "starts")


_NO_ACCENTS = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")


def _compose_item(it: Any, w: str) -> dict:
    """Пункт направляемого письма: q — задание, checks — признаки (label + any / all / starts / re, if — условие),
    words: [мин, макс], sentences — минимум предложений, sample — образец, sample_ru — его перевод."""
    if not isinstance(it, dict) or not str(it.get("q") or "").strip():
        raise ContentError(f"{w}: у письма нужен q (задание)")
    checks = []
    for c in _items(it.get("checks")):
        if not isinstance(c, dict) or not str(c.get("label") or "").strip():
            raise ContentError(f"{w}: у признака нужен label")
        # \w в браузере не знает ñ и ü, а в Python знает: приводим к одному набору букв. Текст ученика сравнивается
        # без ударений (как на странице), поэтому и из выражения ударения убираем: «\w+ía» ищет «vivia».
        check = {"label": str(c["label"]).strip(),
                 "re": str(c.get("re") or "").strip().replace("\\w", "[a-zñü0-9]").translate(_NO_ACCENTS),
                 "if": [str(x).strip() for x in _items(c.get("if"))]}
        for key in (*CHECK_KEYS, "if"):
            if any(isinstance(x, bool) for x in _items(c.get(key))):   # YAML читает no / sí без кавычек как false / true
                raise ContentError(f"{w}: в признаке «{check['label']}» слова no, yes, on, off пишите в кавычках")
        for key in CHECK_KEYS:
            check[key] = [str(x).strip() for x in _items(c.get(key))]
        if not (check["re"] or any(check[k] for k in CHECK_KEYS)):
            raise ContentError(f"{w}: у признака «{check['label']}» нужен any, all, starts или re")
        if check["re"]:
            try:
                re.compile(check["re"])
            except re.error as exc:
                raise ContentError(f"{w}: ошибка в re признака «{check['label']}»: {exc}") from exc
        checks.append(check)
    words = it.get("words")
    if words is not None:
        if not (isinstance(words, (list, tuple)) and len(words) == 2 and all(isinstance(x, int) for x in words) and 0 < words[0] <= words[1]):
            raise ContentError(f"{w}: words — [минимум, максимум] слов")
        words = [int(words[0]), int(words[1])]
    sample = str(it.get("sample") or "").strip()
    if not sample:
        raise ContentError(f"{w}: у письма нужен образец (sample)")
    return {"q": str(it["q"]).strip(), "format": str(it.get("format") or "").strip(), "words": words,
            "sentences": int(it.get("sentences") or 0), "checks": checks, "sample": sample,
            "sample_ru": str(it.get("sample_ru") or "").strip(), "explain": str(it.get("explain") or "").strip(),
            "meta": _item_meta(it, w)}


def _scenario_block(btype: str, value: Any, w: str) -> Block:
    """Блоки сценария урока сайта (learn, choose, write, match, sort, build, mission, more, recap, review)."""
    spec = value if isinstance(value, dict) else None
    if btype == "recap":
        spec = spec or {}
        return Block(btype, {"title": str(spec.get("title") or "").strip(), "words": spec.get("words", True) is not False,
                             "phrase": str(spec.get("phrase") or "").strip()})
    if btype == "review":
        if spec is None or not _items(spec.get("skills")):
            raise ContentError(f"{w}: нужен список skills")
        n = int(spec.get("n") or 2)
        if not 1 <= n <= 3:
            raise ContentError(f"{w}: n — от 1 до 3 (повторение не должно раздувать урок)")
        return Block(btype, {"title": str(spec.get("title") or "").strip(), "skills": [str(x).strip() for x in _items(spec["skills"])], "n": n})
    if btype == "learn":
        words = [str(v).strip() for v in _items(value)]
        if not words:
            raise ContentError(f"{w}: нужен список слов урока")
        return Block(btype, words)
    if btype in ("mission", "more"):
        if spec is None:
            spec = {"text": value}
        if not str(spec.get("text") or "").strip():
            raise ContentError(f"{w}: нужен text")
        title = spec.get("title") or ("Подробнее" if btype == "more" else "")
        return Block(btype, {"title": str(title).strip(), "text": str(spec["text"]).strip()})
    if btype == "compose":
        if spec is None:
            raise ContentError(f"{w}: нужен словарь с items")
        items = [_compose_item(it, w) for it in _items(spec.get("items") or ([spec] if spec.get("sample") else []))]
        if not items:
            raise ContentError(f"{w}: нужен хотя бы один пункт (q, checks, sample)")
        return Block(btype, {"title": str(spec.get("title") or "").strip(), "items": items})
    if btype == "chat":
        if spec is None or not _items(spec.get("turns")):
            raise ContentError(f"{w}: нужен список turns")
        who = str(spec.get("with") or "").strip()
        if not who:
            raise ContentError(f"{w}: нужен собеседник (with: Имя)")
        items, end = [], []
        for t in _items(spec["turns"]):
            if not isinstance(t, dict) or not t.get("say"):
                raise ContentError(f"{w}: у хода нужна реплика собеседника say: «испанский | перевод»")
            es, _, ru = str(t["say"]).partition(" | ")
            line = (who, es.strip(), ru.strip())
            kinds = [k for k in ("build", "write", "choose", "compose") if k in t]
            if not kinds:
                end.append(line)
                continue
            if len(kinds) > 1 or end:
                raise ContentError(f"{w}: у хода один вид ответа (build, write, choose или compose); реплики без ответа — только в конце")
            kind = kinds[0]
            item: dict = {"kind": kind, "line": line, "task": str(t.get("task") or "").strip(),
                          "explain": str(t.get("explain") or "").strip(), "meta": _item_meta(t, w)}
            if kind == "build":
                b = t["build"] if isinstance(t["build"], dict) else {"es": t["build"]}
                item.update(es=str(b["es"]).strip(), ru=str(b.get("ru") or t.get("ru") or "").strip(),
                            alt=_alts(b.get("alt")), extra=[str(x).strip() for x in _items(b.get("extra"))])
            elif kind == "write":
                item.update(answers=_alts(t["write"]), format=str(t.get("format") or "").strip())
                if not item["answers"]:
                    raise ContentError(f"{w}: у хода с write нет ответа")
            elif kind == "choose":
                item.update(options=_options(t["choose"]))
            else:
                c = t["compose"] if isinstance(t["compose"], dict) else {}
                item.update(_compose_item({**c, "q": item["task"] or "—"}, w))
                item["task"] = item["task"] or ""
                item["meta"] = _item_meta(t, w)
            items.append(item)
        if not items:
            raise ContentError(f"{w}: в разговоре нет ни одного ответа ученика")
        return Block(btype, {"title": str(spec.get("title") or "").strip(), "who": who, "items": items, "end": end})
    if btype == "sort" and spec is not None and "groups" not in spec:   # sort: {el: [...], la: [...]}
        spec = {"title": spec.get("title"), "groups": {k: v for k, v in spec.items() if k != "title"}}
    if spec is None:
        spec = {"pairs": value} if btype == "match" else {"groups": value} if btype == "sort" else {"items": value}
    head = {"title": str(spec.get("title") or "").strip()}
    if btype in ("choose", "write", "build") and any(isinstance(it, dict) and it.get("variants") for it in _items(spec.get("items"))):
        spec = {**spec, "items": _with_variants(_items(spec.get("items")), w)}
    if btype == "choose":
        items = []
        for it in _items(spec.get("items")):
            if not isinstance(it, dict) or "options" not in it:
                raise ContentError(f"{w}: у вопроса нужны options (первый вариант — верный): {it!r}")
            items.append({
                "q": str(it.get("q") or "").strip(), "options": _options(it["options"]),
                "explain": str(it.get("explain") or "").strip(), "say": str(it.get("say") or "").strip(),
                "lines": [_line(x, w) for x in _items(it.get("lines"))], "img": str(it.get("img") or "").strip(),
                "meta": _item_meta(it, w), "noaudio": _noaudio(it.get("noaudio"), "choose", w),
                **({"vg": it["vg"]} if "vg" in it else {}),
            })
        return Block(btype, {**head, "items": items})
    if btype == "write":
        items = []
        for it in _items(spec.get("items")):
            if isinstance(it, dict):
                q, answers = str(it.get("q") or "").strip(), _alts(it.get("a"))
                extra = {k: str(it.get(k) or "").strip() for k in ("explain", "say", "format", "img", "answer")}
                extra["meta"], extra["noaudio"] = _item_meta(it, w), _noaudio(it.get("noaudio"), "write", w)
            else:
                q, found, a = str(it).partition(" => ")
                if not found:
                    raise ContentError(f"{w}: строка ввода — «вопрос => ответ | другой ответ»: {it!r}")
                q, answers = q.strip(), _alts(a)
                extra = {"explain": "", "say": "", "format": "", "img": "", "answer": "", "meta": {"mistakes": {}}, "noaudio": None}
            items.append({"q": q, "answers": answers, **extra, **({"vg": it["vg"]} if isinstance(it, dict) and "vg" in it else {})})
        accents = str(spec.get("accents") or "soft")
        if accents not in ("soft", "strict"):
            raise ContentError(f"{w}: accents — soft или strict")
        # answer: number | time | phone | date — ответ цифрами сравнивается по смыслу (03:30 = 3:30, 648 20 71 93 = 648207193).
        kind = str(spec.get("answer") or "").strip()
        for it in items:
            it["answer"] = it["answer"] or kind
            if it["answer"] and it["answer"] not in ANSWER_KINDS:
                raise ContentError(f"{w}: answer — {', '.join(ANSWER_KINDS)}")
            if it["answer"] and not any(re.search(r"\d", a) for a in it["answers"]):
                raise ContentError(f"{w}: answer: {it['answer']} — нужен ответ цифрами: {it['q'][:40]!r}")
        return Block(btype, {**head, "format": str(spec.get("format") or "").strip(), "accents": accents, "items": items})
    if btype == "match":
        pairs = []
        for p in _items(spec.get("pairs")):
            left, right = (str(p[0]).strip(), str(p[1]).strip()) if isinstance(p, (list, tuple)) else split_pair(p, w)
            pairs.append((left, right))
        return Block(btype, {**head, "pairs": pairs})
    if btype == "sort":
        raw = spec.get("groups") or {}
        groups = ([(str(k).strip(), [str(x).strip() for x in _items(v)]) for k, v in raw.items()]
                  if isinstance(raw, dict) else
                  [(str(g["name"]).strip(), [str(x).strip() for x in _items(g.get("items"))]) for g in _items(raw)])
        return Block(btype, {**head, "groups": groups})
    if btype == "build":
        items = []
        for it in _items(spec.get("items")):
            if isinstance(it, dict):
                es, ru = str(it["es"]).strip(), str(it.get("ru") or "").strip()
                alt, extra = _alts(it.get("alt")), [str(x).strip() for x in _items(it.get("extra"))]
                meta = _meta(it, w)
            else:
                (es, ru), alt, extra, meta = split_pair(it, w), [], [], {}
            items.append({"es": es, "ru": ru, "alt": alt, "extra": extra, "meta": meta,
                          **({"vg": it["vg"]} if isinstance(it, dict) and "vg" in it else {})})
        return Block(btype, {**head, "items": items})
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
        meta=_meta(raw, where),
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
        goal=str(raw.get("goal") or "").strip(),
        version=int(raw.get("version") or 1),
        check=str(raw.get("check") or "").strip(),
        cover_subtitle=str(raw.get("cover_subtitle") or "").strip(),
    )
    if lesson.check not in CHECKS:
        raise ContentError(f"{where}: check — control или soft")
    if lesson.version < 1:
        raise ContentError(f"{where}: version — целое число от 1")
    for item in lesson.vocab:
        item.lesson = lesson
    return lesson


def load_skills(content_dir: Path) -> dict[str, dict]:
    """Реестр навыков сайта: тег → название, урок, где навык вводится (id урока), и объяснение (id блока)."""
    path = Path(content_dir) / "skills.yaml"
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out = {}
    for tag, spec in raw.items():
        if not isinstance(spec, dict) or not spec.get("title") or not spec.get("lesson"):
            raise ContentError(f"skills.yaml: у навыка {tag} нужны title и lesson")
        out[str(tag)] = {"title": _text(spec["title"]), "lesson": str(spec["lesson"]), "rule": str(spec.get("rule") or "")}
    return out


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
            goals=[_text(g) for g in data.get("goals", []) or []],
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

    clues_path = content_dir / "clues.yaml"
    clues = yaml.safe_load(clues_path.read_text(encoding="utf-8")) or {} if clues_path.exists() else {}
    by_es = {item.es: item for lesson in lessons for item in lesson.vocab}
    for es, clue in clues.items():
        if es not in by_es:
            raise ContentError(f"clues.yaml: нет такого слова в курсе: {es}")
        by_es[es].clue = _text(clue)

    return Course(
        title=str(meta.get("title", "Español")),
        channel=str(meta.get("channel", "")),
        units=units,
        lessons=lessons,
        names=names,
        meta_words={str(w).lower() for w in meta.get("meta_words", []) or []},
        settings=settings,
        bot=str(meta.get("bot", "") or "").lstrip("@"),
        skills=load_skills(content_dir),
    )
