"""Проверка всего курса: словарь, лимиты Telegram, разметка, постепенность."""

from espanol.course import parse_vocab, parse_vocab_line
from espanol.markup import check_html, plain, visible_len
from espanol.render import AudioMessage, PollMessage, TextMessage, poll_problems


def test_course_has_no_unknown_words(lexicon):
    issues = [str(i) for i in lexicon.check()]
    assert issues == []


def test_every_message_fits_telegram_limits(course, renderer):
    for lesson in course.lessons:
        messages = renderer.render(lesson)
        assert isinstance(messages[0], TextMessage), lesson.id
        for message in messages:
            if isinstance(message, TextMessage):
                assert visible_len(message.html) <= 4096, lesson.id
                assert check_html(message.html) == [], lesson.id
            elif isinstance(message, PollMessage):
                assert poll_problems(message) == [], lesson.id
                assert 0 <= message.correct < len(message.options)
            elif isinstance(message, AudioMessage):
                assert message.segments, lesson.id


def test_hidden_sections_go_in_separate_messages(course, renderer):
    """Telegram открывает все спойлеры сообщения разом — у каждой рубрики свои ответы."""
    for lesson in course.lessons:
        messages = renderer.render(lesson)
        texts = [m for m in messages if isinstance(m, TextMessage)]
        for message in texts:
            hidden = [p for p in message.html.split("\n\n") if "<tg-spoiler>" in p]
            assert len(hidden) <= 1, lesson.id
        assert not texts[0].silent and all(m.silent for m in messages[1:]), lesson.id
        recall = [n for n, m in enumerate(messages) if n and isinstance(m, TextMessage)
                  and m.html.startswith(renderer._label("recall", lesson))]
        audio = [n for n, m in enumerate(messages) if isinstance(m, AudioMessage)]
        if recall and audio:
            assert audio[0] < recall[0], lesson.id


def test_auto_generated_text_uses_only_known_words(course, renderer):
    """Повторения и автотесты собираются из пройденных слов — проверяем и их."""
    for lesson in course.lessons:
        manual = {plain(q.question) for q in lesson.quiz}  # ручные вопросы проверяет валидатор
        for message in renderer.render(lesson):
            if isinstance(message, PollMessage) and message.question not in manual:
                texts = [message.question, message.options[message.correct]]
                for text in texts:
                    assert renderer.lexicon.unknown_words(text, lesson) == [], (lesson.id, text)


def test_small_steps(course):
    limit = course.settings["max_new_words"]
    assert all(len(lesson.vocab) <= limit for lesson in course.lessons)


def test_intro_lesson_is_number_zero(course, renderer):
    assert course.lesson(0) is course.lessons[0]
    assert "Урок 0" in renderer.render(course.lessons[0])[0].html
    assert course.lesson(len(course.lessons) - 1) is course.lessons[-1]


def test_lesson_ids_are_unique(course):
    ids = [lesson.id for lesson in course.lessons]
    assert len(ids) == len(set(ids))


def test_course_goes_from_a0_to_a1(course):
    levels = [lesson.level for lesson in course.lessons]
    assert levels[0] == "A0" and levels[-1] == "A1"
    assert levels == sorted(levels)  # A0 не встречается после A1


def test_immersion_labels_switch_to_spanish(course, renderer):
    first = renderer.render(course.lessons[1])[0].html
    last = renderer.render(course.lessons[-2])[0].html
    assert "Урок 1" in first
    assert f"Lección {course.lessons[-2].number}" in last


def test_vocab_line_parsing():
    data = parse_vocab_line("👋 ¡Hola! [о́ла] — привет {pos: word} :: ¡Hola, Ana! — Привет, Анна!", "test")
    assert data["emoji"] == "👋" and data["es"] == "¡Hola!" and data["pron"] == "о́ла"
    assert data["ru"] == "привет" and data["pos"] == "word"
    assert data["ex"] == "¡Hola, Ana! — Привет, Анна!"


def test_vocab_item_inference():
    noun = parse_vocab("el profesor / la profesora — преподаватель", "test")
    assert noun.pos == "noun" and noun.cores == ["profesor", "profesora"]
    adj = parse_vocab("alto/a — высокий", "test")
    assert adj.pos == "adj" and adj.base_forms() == {"alto", "alta"}
    verb = parse_vocab("llamarse — называться {forms: llamo}", "test")
    assert verb.pos == "verb" and {"llamarse", "llamar", "llamo"} <= verb.base_forms()


def test_rich_articles_fit_telegram_limits(course, renderer):
    from espanol.rich import RichRenderer, rich_problems

    rich = RichRenderer(renderer, images=True)
    for lesson in course.lessons:
        article = rich.render(lesson)[0]
        assert rich_problems(article) == [], lesson.id


def test_recall_block_has_at_least_min_words(course, schedule):
    """«Вспомним» не сжимается до одного слова: недостающие добираются из давно не встречавшихся."""
    minimum = course.settings["srs"]["recall_min"]
    for lesson in course.lessons[2:]:
        if lesson.kind in ("review", "quiz", "final", "intro", "finale"):
            continue
        assert len(schedule.picks_for(lesson)) >= minimum, lesson.id


def test_lookalike_words_are_asked_as_riddles(course, renderer, lexicon):
    """«Как по-испански «тортилья»?» — ответ в самом вопросе; такие слова спрашиваем загадкой."""
    from espanol.quizgen import looks_alike

    alike = [item for item in lexicon.items if looks_alike(item)]
    assert all(item.clue for item in alike), [i.es for i in alike if not i.clue]
    for lesson in course.lessons:
        for message in renderer.render(lesson):
            if isinstance(message, PollMessage):
                for item in alike:
                    assert f"«{plain(item.ru)}»" not in message.question, (lesson.id, item.es)
