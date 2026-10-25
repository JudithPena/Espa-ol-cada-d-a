"""«Мои слова»: личная колода автора в боте на Cloudflare (вне курса и канала).

Автор присылает Claude список слов, Claude пишет к каждому карточку-разбор
в content/mis_palabras/NN_имя.yaml (правила — docs/mis_palabras_guide.md),
а бот каждый день даёт 10 новых карточек и повторения по интервалам.

    python -m espanol palabras            # сколько слов в колоде
    python -m espanol palabras querer     # карточка слова так, как её покажет бот

Порядок слов в колоде — порядок файлов, внутри файла — порядок слов: новые слова бот берёт по порядку.
id слова — хеш языка и написания (или поле id): по нему бот помнит, как автор знает слово.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .course import ContentError
from .markup import check_html, escape, plain, tg_len, to_html, visible_len

FOLDER = "mis_palabras"
LANGS = {"es": ("🇬🇧", "По-английски"), "en": ("🇪🇸", "По-испански")}  # язык слова → раздел аналогов
SPEAKER = re.compile(r"^([\w ]{1,15}):\s+(.+)$")
CEFR = re.compile(r"^(A1|A2|B1|B2|C1|C2)\b")
CARD_LIMIT = 4000  # Telegram — 4096 символов, остаток — на заголовок карточки в боте
BACK_LIMIT = 900   # оборот карточки — подпись к аудио, у неё лимит 1024
REQUIRED = ("word", "ru", "ipa", "meaning", "examples", "origin", "register", "synonyms", "analogs",
            "dialogue", "cefr", "frequency", "collocations", "collocation_example", "trap")


@dataclass
class Synonym:
    word: str
    pair: list[str]   # то же предложение: с разбираемым словом и с синонимом
    diff: list[str]   # разница в оттенке или стиле


@dataclass
class Word:
    id: str
    word: str
    lang: str
    ru: str            # короткий перевод — для повторения
    ipa: str
    meaning: str
    examples: list[tuple[str, str]]
    say: str = ""      # примерно русскими буквами
    pron: str = ""     # особенности произношения
    homonym: str = ""  # слово уже было в колоде в другом значении
    origin: str = ""
    register: str = ""
    synonyms: list[Synonym] = field(default_factory=list)
    analogs: list[str] = field(default_factory=list)
    dialogue: list[tuple[str, str]] = field(default_factory=list)
    cefr: str = ""
    frequency: str = ""
    collocations: list[str] = field(default_factory=list)
    collocation_example: tuple[str, str] | None = None
    trap: str = ""
    source: str = ""
    problems: list[str] = field(default_factory=list)  # найдены при загрузке, выводит validate


def word_id(lang: str, word: str) -> str:
    return hashlib.sha1(f"{lang}|{word}".encode("utf-8")).hexdigest()[:10]


def _pair(text: Any, sep: str = " — ") -> tuple[str, str] | None:
    """«оригинал — перевод»: делим по последнему тире, в оригинале своё тире может быть."""
    text = str(text or "").strip()
    if sep not in text:
        return None
    left, right = text.rsplit(sep, 1)
    return left.strip(), right.strip()


def _lines(raw: Any) -> list[str]:
    items = [raw] if isinstance(raw, str) else list(raw or [])
    return [str(x).strip() for x in items if str(x).strip()]


def load_deck(content_dir: str | Path) -> list[Word]:
    words: list[Word] = []
    for path in sorted((Path(content_dir) / FOLDER).glob("*.yaml")):
        where = f"{FOLDER}/{path.name}"
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ContentError(f"{where}: ошибка YAML: {exc}") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("words"), list):
            raise ContentError(f"{where}: нужен список words")
        lang = str(raw.get("lang", "es"))
        for n, entry in enumerate(raw["words"], 1):
            if not isinstance(entry, dict) or not entry.get("word"):
                raise ContentError(f"{where}, слово {n}: нет поля word")
            words.append(_parse(entry, str(entry.get("lang", lang)), f"{where}, «{entry['word']}»"))
    return words


def _parse(raw: dict, lang: str, where: str) -> Word:
    problems = [f"нет раздела {key}" for key in REQUIRED if key not in raw]
    if lang not in LANGS:
        problems.append(f"язык {lang!r}: бывает es или en")
    examples = []
    for ex in _lines(raw.get("examples")):
        pair = _pair(ex)
        if pair:
            examples.append(pair)
        else:
            problems.append(f"пример без перевода через « — »: {ex}")
    synonyms = []
    for syn in raw.get("synonyms") or []:
        if not isinstance(syn, dict) or not syn.get("word") or len(_lines(syn.get("pair"))) != 2:
            problems.append("синоним: нужны word, pair (два предложения) и diff")
            continue
        synonyms.append(Synonym(str(syn["word"]).strip(), _lines(syn["pair"]), _lines(syn.get("diff"))))
    dialogue = []
    for line in _lines(raw.get("dialogue")):
        pair = _pair(line, " | ")
        if pair:
            dialogue.append(pair)
        else:
            problems.append(f"реплика без перевода через « | »: {line}")
    colloc_example = _pair(raw.get("collocation_example"))
    if raw.get("collocation_example") and not colloc_example:
        problems.append("collocation_example — «пример — перевод»")
    word = str(raw["word"]).strip()
    return Word(
        id=str(raw.get("id") or word_id(lang, word)), word=word, lang=lang,
        ru=str(raw.get("ru", "")).strip(), ipa=str(raw.get("ipa", "")).strip(),
        meaning=str(raw.get("meaning", "")).strip(), examples=examples,
        say=str(raw.get("say", "")).strip(), pron=str(raw.get("pron", "")).strip(),
        homonym=str(raw.get("homonym", "")).strip(), origin=str(raw.get("origin", "")).strip(),
        register=str(raw.get("register", "")).strip(), synonyms=synonyms,
        analogs=_lines(raw.get("analogs")), dialogue=dialogue, cefr=str(raw.get("cefr", "")).strip(),
        frequency=str(raw.get("frequency", "")).strip(), collocations=_lines(raw.get("collocations")),
        collocation_example=colloc_example, trap=str(raw.get("trap", "")).strip(),
        source=where, problems=problems,
    )


def _example(pair: tuple[str, str]) -> str:
    return f"<i>{to_html(pair[0])}</i> — {to_html(pair[1])}"


def _quote(lines: list[str]) -> str:
    """Раскрывающийся блок: в свёрнутом виде Telegram показывает первые строки."""
    return "<blockquote expandable>" + "\n".join(lines).strip() + "</blockquote>"


def render_card(w: Word) -> str:
    """Полная карточка-разбор (HTML Telegram). Главное — сразу, подробности — в раскрывающихся блоках."""
    head = [f"<b>{escape(w.word)}</b> — {to_html(w.ru)}",
            "🗣 " + escape(w.ipa) + (f" · {escape(w.say)}" if w.say else ""),
            to_html(w.pron) if w.pron else "Особенностей произношения нет."]
    if w.homonym:
        head += ["", "⚠️ " + to_html(w.homonym)]
    head += ["", f"📖 <b>Значение.</b> {to_html(w.meaning)}"]
    head += [f"• {_example(ex)}" for ex in w.examples]

    more = []
    if w.origin:
        more += [f"🧩 <b>Происхождение.</b> {to_html(w.origin)}", ""]
    if w.register:
        more += [f"🎚 <b>Регистр.</b> {to_html(w.register)}", ""]
    for syn in w.synonyms:
        more += [f"🔄 <b>Синоним: {escape(syn.word)}</b>"]
        more += [f"• <i>{to_html(s)}</i>" for s in syn.pair]
        more += [f"– {to_html(d)}" for d in syn.diff] + [""]
    if not w.synonyms:
        more += ["🔄 Близких синонимов нет.", ""]
    if w.analogs:
        flag, title = LANGS.get(w.lang, LANGS["es"])
        more += [f"{flag} <b>{title}</b>"] + [f"• {to_html(a)}" for a in w.analogs]

    dialogue = []
    if w.dialogue:
        dialogue = ["💬 <b>Мини-диалог</b>"]
        for line, ru in w.dialogue:
            m = SPEAKER.match(line)  # «Ana: …» — имя жирным
            line = f"<b>{escape(m.group(1))}:</b> {to_html(m.group(2))}" if m else to_html(line)
            dialogue += [f"— {line}", f"   <i>{to_html(ru)}</i>"]

    usage = []
    if w.cefr:
        usage += [f"📊 <b>Уровень</b> {to_html(w.cefr)}"]
    if w.frequency:
        usage += [f"📈 <b>Частотность.</b> {to_html(w.frequency)}"]
    if w.collocations:
        usage += ["", "🔗 <b>Сочетания</b>"] + [f"• {to_html(c)}" for c in w.collocations]
        if w.collocation_example:
            usage += [_example(w.collocation_example)]
    if w.trap:
        usage += ["", f"🪤 <b>Ловушка.</b> {to_html(w.trap)}"]

    parts = ["\n".join(head)] + [_quote(block) for block in (more, dialogue, usage) if block]
    return "\n\n".join(parts)


def back_text(w: Word) -> str:
    """Оборот карточки при повторении (без заголовка): слово, перевод и первый пример — как в боте."""
    text = f"{w.word} {w.ipa}\n— {plain(w.ru)}"
    if w.examples:
        text += f"\n\n{plain(w.examples[0][0])} — {plain(w.examples[0][1])}"
    return text


def deck_problems(words: list[Word]) -> list[str]:
    problems: list[str] = []
    seen: dict[str, str] = {}
    for w in words:
        where = w.source
        problems += [f"{where}: {p}" for p in w.problems]
        if w.id in seen:
            problems.append(f"{where}: такое слово уже есть ({seen[w.id]}). Если это другое значение, "
                            "дайте ему свой id и заполните homonym")
        seen[w.id] = where
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", w.id):
            problems.append(f"{where}: id — латиница, цифры, «-» и «_», до 40 символов")
        if not 2 <= len(w.examples) <= 4:
            problems.append(f"{where}: примеров {len(w.examples)}, нужно 2–4")
        if len(w.synonyms) > 2:
            problems.append(f"{where}: синонимов больше двух")
        if w.dialogue and not 2 <= len(w.dialogue) <= 4:
            problems.append(f"{where}: в мини-диалоге 2–4 реплики")
        if w.collocations and not 3 <= len(w.collocations) <= 5:
            problems.append(f"{where}: сочетаний {len(w.collocations)}, нужно 3–5")
        if w.cefr and not CEFR.match(w.cefr):
            problems.append(f"{where}: cefr начинается с уровня A1…C2")
        if "🇷🇺" in str(w.__dict__):
            problems.append(f"{where}: флаг 🇷🇺 не ставим — автор из Украины")
        card = render_card(w)
        if visible_len(card) > CARD_LIMIT:
            problems.append(f"{where}: карточка длиннее {CARD_LIMIT} символов ({visible_len(card)}) — сократите")
        problems += [f"{where}: {p}" for p in check_html(card)]
        if tg_len(back_text(w)) > BACK_LIMIT:
            problems.append(f"{where}: перевод и первый пример длиннее {BACK_LIMIT} символов")
    return problems


def find_word(words: list[Word], ref: str) -> Word:
    for w in words:
        if ref in (w.id, w.word) or ref.lower() == w.word.lower():
            return w
    raise ContentError(f"в колоде нет слова «{ref}»")


def record(w: Word, audio: str = "") -> dict:
    """Слово для бота (bot/data/mywords.json)."""
    return {
        "id": w.id,
        "word": w.word,
        "lang": w.lang,
        "ru": plain(w.ru),
        "ipa": w.ipa,
        "ex": [plain(w.examples[0][0]), plain(w.examples[0][1])] if w.examples else None,
        "card": render_card(w),
        "audio": audio,
    }
