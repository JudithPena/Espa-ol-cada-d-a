from collections import Counter

from espanol.lexicon import Lexicon
from espanol.srs import Schedule


def test_schedule_is_deterministic(course, schedule):
    again = Schedule(course, Lexicon(course))
    for p, picks in schedule.picks.items():
        assert [x.item.es for x in picks] == [x.item.es for x in again.picks[p]]


def test_words_are_reviewed_only_after_introduction(course, schedule):
    for p, picks in schedule.picks.items():
        for pick in picks:
            assert pick.item.lesson.index < p


def test_almost_every_word_comes_back(course, lexicon, schedule):
    """Каждое слово хоть раз возвращается: в повторении или в новом тексте."""
    reviewed = Counter(id(pick.item) for picks in schedule.picks.values() for pick in picks)
    exposed = Counter(idx for found in schedule.exposed.values() for idx in found)
    orphans = [
        item.es for idx, item in enumerate(lexicon.items)
        if item.srs and not reviewed[id(item)] and not exposed[idx]
    ]
    last_unit = course.units[-1].id
    assert all(lexicon.items[[i.es for i in lexicon.items].index(es)].lesson.unit.id == last_unit
               for es in orphans), orphans


def test_review_posts_are_full(course, schedule):
    for lesson in course.lessons:
        if lesson.kind == "review":
            assert len(schedule.picks_for(lesson)) >= 10, lesson.id


def test_production_after_two_reviews(schedule):
    stages = {pick.stage: pick.production for picks in schedule.picks.values() for pick in picks}
    assert stages.get(1) is False and stages.get(3) is True
