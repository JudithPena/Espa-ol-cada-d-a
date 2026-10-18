import pytest

from espanol.course import ContentError
from espanol.markup import to_html
from espanol.render import PollMessage
from espanol.rich import RichMessage
from espanol.videos import VideoRenderer, VideoWords, check_video, find_video, load_videos, video_problems

from conftest import CONTENT

VIDEO = """
title: Тест
url: https://example.com/v
after: {after}
transcript: |
  Hola. Yo como pan con mermelada.
translation: |
  Привет. Я ем хлеб с джемом.
vocab:
{vocab}
blocks:
  - "Подробнее — в уроке [[comida/er_ir]]."
quiz:
  - q: "Что он ест?"
    options: "pan | queso"
"""

VOCAB = """  - "🍽 comer — есть {forms: como}"
  - "🍞 el pan — хлеб"
  - "➕ con — с"
  - "🍓 la mermelada — джем"
"""


def write(tmp_path, course, after=13, vocab=VOCAB):
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "01_test.yaml").write_text(VIDEO.format(after=after, vocab=vocab), encoding="utf-8")
    return load_videos(tmp_path, course)


def test_course_videos_are_valid(course, lexicon, renderer):
    assert video_problems(load_videos(CONTENT, course), lexicon, renderer) == []


def test_video_does_not_change_course(course):
    load_videos(CONTENT, course)
    assert all(lesson.kind != "video" for lesson in course.lessons)


def test_find_video_by_number_or_id(tmp_path, course):
    videos = write(tmp_path, course)
    assert find_video(videos, "video:1").id == "test"
    assert find_video(videos, "video:test").number == 1
    with pytest.raises(KeyError):
        find_video(videos, "video:2")


def test_lesson_refs_are_expanded(tmp_path, course):
    video = write(tmp_path, course)[0]
    target = course.lesson("comida/er_ir")
    assert video.lesson.blocks[0].data == f"Подробнее — в уроке {target.number} «{target.title}»."


def test_unknown_ref_is_an_error(tmp_path, course):
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "01_x.yaml").write_text(
        VIDEO.format(after=13, vocab=VOCAB).replace("comida/er_ir", "nope/nope"), encoding="utf-8")
    with pytest.raises(ContentError):
        load_videos(tmp_path, course)


def test_new_words_must_be_explained(tmp_path, course, lexicon):
    video = write(tmp_path, course, vocab=VOCAB.replace('  - "🍓 la mermelada — джем"\n', ""))[0]
    problems = check_video(video, lexicon)
    assert any("«mermelada»" in p and "в курсе его нет" in p for p in problems)


def test_passed_words_are_not_explained(tmp_path, course, lexicon):
    video = write(tmp_path, course, vocab=VOCAB + '  - "👋 hola — привет"\n')[0]
    assert any("«hola» уже пройдено" in p for p in check_video(video, lexicon))


def test_after_decides_what_is_passed(tmp_path, course, lexicon):
    er_ir = course.lesson("comida/er_ir").number
    video = write(tmp_path, course, after=er_ir)[0]
    assert any("«comer» уже пройдено" in p for p in check_video(video, lexicon))


def test_planned_words_point_to_course_lessons(tmp_path, course, lexicon, renderer):
    video = write(tmp_path, course)[0]
    words = VideoWords(lexicon, video)
    pan, mermelada = video.lesson.vocab[1], video.lesson.vocab[3]
    assert words.planned_lesson(pan).id == "comida/comida1"
    assert words.planned_lesson(mermelada) is None
    messages = VideoRenderer(renderer, lexicon, images=False).render_video(video)
    article = messages[0]
    assert isinstance(article, RichMessage) and all(isinstance(m, PollMessage) for m in messages[1:])
    assert f"Подробнее — в уроке {course.lesson('comida/comida1').number}" in article.html
    assert to_html(video.url) in article.html
    assert "<details><summary>🇷🇺 Перевод</summary>" in article.html
