import pytest

from espanol.course import ContentError
from espanol.markup import to_html
from espanol.render import PollMessage
from espanol.rich import RichMessage
from espanol.videos import VideoRenderer, check_video, find_video, load_videos, video_problems

from conftest import CONTENT

VIDEO = """
title: Тест
url: https://example.com/v
after: {after}
segments:
  - es: "Hola. Yo como pan con mermelada."
    ru: "Привет. Я ем хлеб с джемом."
    words: [comer, el pan, con, la mermelada]
    note: "Пояснение к фразе."
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


def test_publish_at_is_kyiv_time_for_the_bot(tmp_path, course):
    """publish_at — по Киеву; бот получает время в UTC (30 октября Киев уже на зимнем времени, UTC+2)."""
    from espanol.botdata import video_schedule

    (tmp_path / "videos").mkdir()
    path = tmp_path / "videos" / "01_test.yaml"
    path.write_text(VIDEO.format(after=13, vocab=VOCAB) + 'publish_at: "2026-10-30 18:00"\n', encoding="utf-8")
    assert video_schedule(load_videos(tmp_path, course)) == [
        {"number": 1, "title": "Тест", "at": "2026-10-30T16:00:00Z"}]
    for bad in ("2026-10-30 18:30", "30.10.2026 18:00"):
        path.write_text(VIDEO.format(after=13, vocab=VOCAB) + f'publish_at: "{bad}"\n', encoding="utf-8")
        with pytest.raises(ContentError, match="publish_at"):
            load_videos(tmp_path, course)


def test_new_words_must_be_explained(tmp_path, course, lexicon):
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "01_test.yaml").write_text(
        VIDEO.format(after=13, vocab=VOCAB.replace('  - "🍓 la mermelada — джем"\n', ""))
        .replace(", la mermelada]", "]"), encoding="utf-8")
    video = load_videos(tmp_path, course)[0]
    problems = check_video(video, lexicon)
    assert any("«mermelada»" in p and "в курсе его нет" in p for p in problems)


def test_passed_words_are_not_explained(tmp_path, course, lexicon):
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "01_test.yaml").write_text(
        VIDEO.format(after=13, vocab=VOCAB + '  - "👋 hola — привет"\n')
        .replace("words: [comer,", "words: [hola, comer,"), encoding="utf-8")
    video = load_videos(tmp_path, course)[0]
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
    # фраза в оригинале, под ней её слова, пояснение и спрятанный перевод
    segment = article.html.split("<blockquote>Hola. Yo como pan con mermelada.</blockquote>", 1)[1]
    assert segment.index("<b>la mermelada</b>") < segment.index("📝 Пояснение") < segment.index("Привет.")
    assert "<details><summary>🔤 Перевод</summary><p>Привет. Я ем хлеб с джемом.</p></details>" in segment
    assert "🇷🇺" not in article.html and "Подробнее" not in article.html


def test_every_word_stands_under_a_segment(tmp_path, course):
    from espanol.course import ContentError

    with pytest.raises(ContentError, match="ни под одной фразой"):
        write(tmp_path, course, vocab=VOCAB + '  - "🧈 la mantequilla — масло"\n')


def test_note_string_stays_one_paragraph(tmp_path, course, lexicon, renderer):
    video = write(tmp_path, course)[0]
    assert video.segments[0].notes == ["Пояснение к фразе."]
    html = VideoRenderer(renderer, lexicon, images=False).render_video(video)[0].html
    assert html.count("📝") == 1


def test_course_video_notes_are_whole_sentences(course):
    for video in load_videos(CONTENT, course):
        for seg in video.segments:
            assert all(len(note.split()) > 3 for note in seg.notes), seg.notes


SECOND = """
title: Второй
url: https://example.com/v2
after: 13
segments:
  - es: "Yo como pan con mantequilla."
    ru: "Я ем хлеб со сливочным маслом."
    words: [la mantequilla]
vocab:
{vocab}
blocks:
  - "Вторая часть рубрики."
quiz:
  - q: "Что он ест?"
    options: "pan | queso"
"""


def write_two(tmp_path, course, vocab='  - "🧈 la mantequilla — сливочное масло"', words="la mantequilla"):
    write(tmp_path, course)
    text = SECOND.format(vocab=vocab).replace("words: [la mantequilla]", f"words: [{words}]")
    (tmp_path / "videos" / "02_second.yaml").write_text(text, encoding="utf-8")
    return load_videos(tmp_path, course)


def test_words_from_earlier_videos_are_reviewed_not_explained(tmp_path, course, lexicon, renderer):
    video = write_two(tmp_path, course)[1]
    assert check_video(video, lexicon) == []
    html = VideoRenderer(renderer, lexicon, images=True).render_video(video)[0].html
    review = html.split("<h3>🔁 Слова из прошлых разборов</h3>", 1)[1].split("<h3>", 1)[0]
    # comer, el pan, con — из разбора №1: коротко в списке, без карточек; mermelada в тексте нет
    assert review.index("<b>comer</b>") < review.index("<b>el pan</b>") < review.index("<b>con</b>")
    assert "mermelada" not in review
    assert html.count("tg://photo?id=w") == 1  # карточка только у нового слова


def test_earlier_video_words_must_not_be_explained_again(tmp_path, course, lexicon):
    video = write_two(tmp_path, course, vocab='  - "🧈 la mantequilla — масло"\n  - "➕ con — с"',
                      words="la mantequilla, con")[1]
    assert any("«con» уже разобрано в разборе №1" in p for p in check_video(video, lexicon))
