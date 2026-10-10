"""Автоматические опросы-викторины по изученной лексике.

Для каждого слова из расписания повторений строится вопрос «Что значит…?»
(узнавание) или «Как по-испански…?» (воспроизведение — с третьего
повторения). Неверные варианты берутся только из уже изученных слов той же
части речи, а синонимы исключаются, чтобы правильный ответ был один.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from .course import VocabItem
from .markup import escape, plain
from .srs import Pick

MAX_QUESTION = 300
MAX_OPTION = 100
MAX_EXPLANATION = 200


@dataclass
class Poll:
    question: str
    options: list[str]
    correct: int
    explanation: str = ""  # HTML (только <b>/<i>)


def meanings(ru: str) -> set[str]:
    """«доброе утро; добрый день (до обеда)» → {"доброе утро", "добрый день"}."""
    text = re.sub(r"\([^)]*\)", "", plain(ru).lower())
    return {m.strip(" .!?«»") for m in re.split(r"[,;/]", text) if m.strip(" .!?«»")}


def _group(item: VocabItem) -> str:
    return item.pos


def distractors(item: VocabItem, known: list[VocabItem], rng: random.Random, n: int = 3,
                production: bool = False) -> list[VocabItem]:
    target = meanings(item.ru)
    seen_text = {item.es.lower() if production else plain(item.ru).lower()}
    pool = []
    for other in known:
        if other is item or meanings(other.ru) & target:
            continue
        text = other.es.lower() if production else plain(other.ru).lower()
        if text in seen_text or len(text) > MAX_OPTION:
            continue
        seen_text.add(text)
        pool.append(other)
    same = [o for o in pool if _group(o) == _group(item)]
    other = [o for o in pool if _group(o) != _group(item)]
    rng.shuffle(same)
    rng.shuffle(other)
    return (same + other)[:n]


def explanation_for(item: VocabItem) -> str:
    if item.example:
        text = f"<i>{escape(item.example.es)}</i> — {escape(plain(item.example.ru))}"
        if len(plain(item.example.es)) + len(plain(item.example.ru)) + 3 <= MAX_EXPLANATION:
            return text
    return f"<b>{escape(item.es)}</b> — {escape(plain(item.ru))}"[:MAX_EXPLANATION]


def vocab_poll(pick: Pick, known: list[VocabItem], seed: str) -> Poll | None:
    item = pick.item
    rng = random.Random(seed)
    production = pick.production
    wrong = distractors(item, known, rng, production=production)
    if len(wrong) < 2:
        return None
    if production:
        question = f"Как по-испански «{plain(item.ru)}»?"
        options = [item.es] + [w.es for w in wrong]
    else:
        question = f"Что значит «{item.es}»?"
        options = [plain(item.ru)] + [plain(w.ru) for w in wrong]
    order = list(range(len(options)))
    rng.shuffle(order)
    return Poll(
        question=question[:MAX_QUESTION],
        options=[options[i] for i in order],
        correct=order.index(0),
        explanation=explanation_for(item),
    )
