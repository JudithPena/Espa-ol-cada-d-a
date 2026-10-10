from pathlib import Path

import pytest

from espanol.course import load_course
from espanol.lexicon import Lexicon
from espanol.render import Renderer
from espanol.srs import Schedule

CONTENT = Path(__file__).resolve().parent.parent / "content"


@pytest.fixture(scope="session")
def course():
    return load_course(CONTENT)


@pytest.fixture(scope="session")
def lexicon(course):
    return Lexicon(course)


@pytest.fixture(scope="session")
def schedule(course, lexicon):
    return Schedule(course, lexicon)


@pytest.fixture(scope="session")
def renderer(course, lexicon, schedule):
    return Renderer(course, lexicon, schedule)
