"""Интервальные повторения (spaced repetition) для ленты канала.

Канал — общая лента, поэтому интервалы считаются в постах, а не по ответам
конкретного читателя: слово возвращается через 1, 3, 7, 14, 30… постов
(расширяющиеся интервалы, как в системе Лейтнера). Если слово само
встретилось в новом тексте, когда подошёл его срок, это засчитывается как
повторение в контексте — отдельно его не повторяем. Явные повторения
достаются словам, которые давно не появлялись в текстах.

Расписание детерминировано: оно вычисляется по порядку уроков, поэтому
любой пост можно пересобрать и получить тот же результат.
"""

from __future__ import annotations

from dataclasses import dataclass

from .course import Course, Lesson, VocabItem
from .lexicon import Lexicon


@dataclass
class Card:
    idx: int
    intro: int
    unit: str
    due: int
    last: int
    srs: bool
    stage: int = 0


@dataclass
class Pick:
    item: VocabItem
    stage: int  # номер повторения (1 — первое)

    @property
    def production(self) -> bool:
        """С третьего повторения просим вспомнить испанское слово по русскому."""
        return self.stage >= 3


class Schedule:
    def __init__(self, course: Course, lexicon: Lexicon):
        self.course = course
        self.lexicon = lexicon
        self.settings = course.settings["srs"]
        self.picks: dict[int, list[Pick]] = {}
        self.exposed: dict[int, set[int]] = {}
        self._simulate()

    def capacity(self, lesson: Lesson) -> tuple[int, int]:
        """(сколько слов повторить, до скольких добирать, если «созревших» мало)."""
        s = self.settings
        if lesson.kind == "intro":
            return 0, 0
        if lesson.kind == "review":
            n = s["review_size"] if lesson.recall is None else lesson.recall
            return n, n
        if lesson.kind in ("quiz", "final"):
            n = s["quiz_auto"] if lesson.auto_quiz is None else lesson.auto_quiz
            return n, n
        n = s["recall_size"] if lesson.recall is None else lesson.recall
        return n, 0

    def _interval(self, stage: int) -> int:
        intervals = self.settings["intervals"]
        return intervals[min(stage, len(intervals) - 1)]

    def _simulate(self) -> None:
        cards: list[Card] = []
        items = self.lexicon.items
        for lesson in self.course.lessons:
            p = lesson.index
            exposed = self.lexicon.exposures(lesson, [c.idx for c in cards])
            self.exposed[p] = exposed

            n, fill = self.capacity(lesson)
            pool = [c for c in cards if c.srs and c.idx not in exposed]
            due = sorted((c for c in pool if c.due <= p), key=lambda c: (c.due, c.stage, c.intro))
            chosen = due[:n]
            if len(chosen) < fill:
                taken = {c.idx for c in chosen}
                rest = [c for c in pool if c.idx not in taken]
                # сначала слова текущей темы, затем давно не встречавшиеся
                rest.sort(key=lambda c: (c.unit != lesson.unit.id, c.last, c.intro))
                chosen += rest[: fill - len(chosen)]
            for card in chosen:
                card.stage += 1
                card.due = p + self._interval(card.stage)
                card.last = p
            self.picks[p] = [Pick(items[c.idx], c.stage) for c in chosen]

            for card in cards:
                if card.idx in exposed:
                    if card.due <= p:
                        card.stage += 1
                        card.due = p + self._interval(card.stage)
                    card.last = p

            for item in lesson.vocab:
                cards.append(Card(
                    idx=len(cards), intro=p, unit=lesson.unit.id,
                    due=p + self._interval(0), last=p, srs=item.srs,
                ))

    def picks_for(self, lesson: Lesson) -> list[Pick]:
        return self.picks.get(lesson.index, [])
