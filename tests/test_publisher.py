"""Публикация с имитацией Telegram: порядок уроков, продолжение после сбоя, лимит в день."""

import json

import pytest

from espanol.publisher import Publisher, State
from espanol.render import AudioMessage, PollMessage, TextMessage


class FakeAPI:
    def __init__(self, fail_on: int | None = None):
        self.sent: list[tuple] = []
        self.fail_on = fail_on

    def _record(self, item):
        if self.fail_on is not None and len(self.sent) == self.fail_on:
            self.fail_on = None
            raise RuntimeError("сеть упала")
        self.sent.append(item)
        return {"message_id": len(self.sent)}

    def send_message(self, chat_id, html, silent=False):
        return self._record(("text", html))

    def send_poll(self, chat_id, question, options, correct, explanation="", silent=True):
        return self._record(("poll", question))

    def send_audio(self, chat_id, audio, filename, title, performer="", caption="", duration=None,
                   silent=True):
        return self._record(("audio", title))


def make(course, renderer, tmp_path, api, **kw):
    return Publisher(course, renderer, api, "@test", tmp_path / "state.json", delay=0,
                     synth=lambda segments, **_: b"\xff\xf3\x64\xc0" + bytes(140), **kw)


def test_publishes_lessons_in_order(course, renderer, tmp_path):
    api = FakeAPI()
    pub = make(course, renderer, tmp_path, api, posts_per_day=10)
    pub.publish_next()
    pub.publish_next()
    state = State.load(tmp_path / "state.json")
    assert [p["id"] for p in state.published] == [course.lessons[0].id, course.lessons[1].id]
    assert state.current is None
    assert api.sent[0][0] == "text"


def test_daily_limit_and_force(course, renderer, tmp_path):
    api = FakeAPI()
    pub = make(course, renderer, tmp_path, api, posts_per_day=1)
    pub.publish_next()
    result = pub.publish_next()
    assert "уже опубликовано" in result
    assert len(State.load(tmp_path / "state.json").published) == 1
    pub.publish_next(force=True)
    assert len(State.load(tmp_path / "state.json").published) == 2


def test_resume_after_failure_without_duplicates(course, renderer, tmp_path):
    lesson = course.lessons[2]  # урок с текстом, аудио и опросами
    total = len(renderer.render(lesson))
    assert total > 2
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({
        "published": [{"id": l.id, "at": "2000-01-01T00:00:00+00:00"} for l in course.lessons[:2]],
        "current": None,
    }))
    api = FakeAPI(fail_on=1)
    pub = make(course, renderer, tmp_path, api, posts_per_day=10)
    with pytest.raises(RuntimeError):
        pub.publish_next()
    state = State.load(state_path)
    assert state.current == {"id": lesson.id, "sent": 1}
    pub.publish_next()
    assert len(api.sent) == total  # ни одно сообщение не ушло дважды
    assert State.load(state_path).published[-1]["id"] == lesson.id


def test_audio_failure_does_not_block_lesson(course, renderer, tmp_path):
    api = FakeAPI()

    def broken(*_, **__):
        raise OSError("нет сети")

    pub = Publisher(course, renderer, api, "@test", tmp_path / "state.json", delay=0, synth=broken)
    lesson = course.lessons[1]
    messages = renderer.render(lesson)
    assert any(isinstance(m, AudioMessage) for m in messages)
    pub.send(messages, "@test", lesson=lesson)
    kinds = [kind for kind, _ in api.sent]
    assert "audio" not in kinds
    assert kinds.count("text") == sum(isinstance(m, TextMessage) for m in messages)
    assert kinds.count("poll") == sum(isinstance(m, PollMessage) for m in messages)


def test_dry_run_sends_nothing(course, renderer, tmp_path, capsys):
    api = FakeAPI()
    pub = make(course, renderer, tmp_path, api)
    result = pub.publish_next(dry_run=True)
    assert "dry-run" in result and api.sent == []
    assert "Урок 1" in capsys.readouterr().out
    assert not (tmp_path / "state.json").exists()


def test_course_finished(course, renderer, tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({
        "published": [{"id": l.id, "at": "2000-01-01T00:00:00+00:00"} for l in course.lessons],
    }))
    pub = make(course, renderer, tmp_path, FakeAPI())
    assert "полностью опубликован" in pub.publish_next()
