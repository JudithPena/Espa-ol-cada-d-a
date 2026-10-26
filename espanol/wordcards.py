"""Карточки слов курса для повторения в боте (/repaso): короткий разбор каждого слова.

Новое слово ученик сначала видит карточкой, потом выбирает перевод из вариантов (bot/src/deck.js).
Короткий разбор пишет Claude в content/repaso/NN_тема.yaml (правила — docs/repaso_guide.md):

    words:
      - es: la casa            # слово ровно как в уроке (поле es)
        pron: "…"              # особенности чтения — если есть
        meaning: "…"           # что значит, когда говорят
        examples: ["Es mi casa. — Это мой дом."]   # 1–3, только пройденные к уроку слова
        collocations: ["en casa — дома"]           # необязательно
        trap: "…"              # необязательно

Если разбора ещё нет, карточка собирается из урока: слово, чтение, перевод и пример.

    python -m espanol carta "la casa"   # карточка слова так, как её покажет бот
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .course import ContentError, Course, VocabItem
from .lexicon import Lexicon
from .markup import check_html, escape, plain, to_html, visible_len

FOLDER = "repaso"
CARD_LIMIT = 4000


@dataclass
class WordCard:
    es: str
    meaning: str = ""
    pron: str = ""
    examples: list[tuple[str, str]] = field(default_factory=list)
    collocations: list[str] = field(default_factory=list)
    trap: str = ""
    source: str = ""
    problems: list[str] = field(default_factory=list)


def _pair(text: str) -> tuple[str, str] | None:
    if " — " not in text:
        return None
    left, right = text.rsplit(" — ", 1)
    return left.strip(), right.strip()


def load_cards(content_dir: str | Path) -> dict[str, WordCard]:
    """Разборы по ключу слова (es в нижнем регистре)."""
    cards: dict[str, WordCard] = {}
    for path in sorted((Path(content_dir) / FOLDER).glob("*.yaml")):
        where = f"{FOLDER}/{path.name}"
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ContentError(f"{where}: ошибка YAML: {exc}") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("words"), list):
            raise ContentError(f"{where}: нужен список words")
        for n, entry in enumerate(raw["words"], 1):
            if not isinstance(entry, dict) or not entry.get("es"):
                raise ContentError(f"{where}, слово {n}: нет поля es")
            card = WordCard(es=str(entry["es"]).strip(), meaning=str(entry.get("meaning", "")).strip(),
                            pron=str(entry.get("pron", "")).strip(), trap=str(entry.get("trap", "")).strip(),
                            collocations=[str(c).strip() for c in entry.get("collocations") or []],
                            source=f"{where}, «{entry['es']}»")
            for ex in entry.get("examples") or []:
                pair = _pair(str(ex))
                if pair:
                    card.examples.append(pair)
                else:
                    card.problems.append(f"пример без перевода через « — »: {ex}")
            if card.es.lower() in cards:
                card.problems.append(f"слово уже разобрано: {cards[card.es.lower()].source}")
            cards[card.es.lower()] = card
    return cards


def render_card(item: VocabItem, card: WordCard | None = None) -> str:
    """Карточка слова курса (HTML Telegram): разбор, а без него — слово, чтение, перевод и пример из урока."""
    head = f"{escape(item.emoji)} " if item.emoji else ""
    head += f"<b>{escape(plain(item.es))}</b>"
    if item.pron:
        head += f" [{escape(item.pron)}]"
    lines = [f"{head} — {to_html(item.ru)}"]
    if card and card.pron:
        lines.append(f"🗣 {to_html(card.pron)}")
    if card and card.meaning:
        lines += ["", f"📖 <b>Значение.</b> {to_html(card.meaning)}"]
    examples = card.examples if card and card.examples else (
        [(item.example.es, item.example.ru)] if item.example else [])
    if examples:
        lines += [""] + [f"• <i>{to_html(es)}</i> — {to_html(ru)}" for es, ru in examples]
    if card and card.collocations:
        lines += ["", "🔗 <b>Сочетания</b>"] + [f"• {to_html(c)}" for c in card.collocations]
    if card and card.trap:
        lines += ["", f"🪤 <b>Ловушка.</b> {to_html(card.trap)}"]
    return "\n".join(lines)


def card_problems(course: Course, lexicon: Lexicon, cards: dict[str, WordCard]) -> list[str]:
    """Разбор — к слову курса; в примерах только слова, пройденные к уроку этого слова."""
    from .botdata import bot_words

    problems: list[str] = []
    items = {item.key: item for item in bot_words(course)}
    for key, card in cards.items():
        where = card.source
        problems += [f"{where}: {p}" for p in card.problems]
        item = items.get(key)
        if not item:
            problems.append(f"{where}: такого слова нет в уроках (es должно совпадать с уроком)")
            continue
        if not card.meaning:
            problems.append(f"{where}: нет meaning")
        if not 1 <= len(card.examples) <= 3:
            problems.append(f"{where}: примеров {len(card.examples)}, нужно 1–3")
        for es, _ in card.examples:
            unknown = lexicon.unknown_words(es, item.lesson)
            if unknown:
                problems.append(f"{where}: в примере «{plain(es)}» не пройдены к уроку {item.lesson.number}: "
                                + ", ".join(dict.fromkeys(unknown)))
        html = render_card(item, card)
        if visible_len(html) > CARD_LIMIT:
            problems.append(f"{where}: карточка длиннее {CARD_LIMIT} символов")
        problems += [f"{where}: {p}" for p in check_html(html)]
    return problems
