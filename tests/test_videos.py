import pytest

from espanol.markup import to_html
from espanol.render import PollMessage
from espanol.rich import RichMessage
from espanol.videos import VideoRenderer, check_video, find_video, load_videos, video_problems

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
  - "Новая рубрика."
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


def test_post_layout(tmp_path, course, lexicon, renderer):
    video = write(tmp_path, course)[0]
    messages = VideoRenderer(renderer, lexicon, images=False).render_video(video)
    article = messages[0]
    assert isinstance(article, RichMessage) and all(isinstance(m, PollMessage) for m in messages[1:])
    assert to_html(video.url) in article.html
    assert "<h3>📜 Текст видео</h3>" in article.html
    assert article.html.count("<details>") == 1  # упражнений в тестовом разборе нет: свёрнут только перевод
    assert "<details><summary>🔤 <b>Перевод</b></summary>" in article.html
    assert "🇷🇺" not in article.html and "Подробнее" not in article.html
