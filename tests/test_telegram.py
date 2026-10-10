"""Клиент Bot API: формат запросов и повтор при ограничении частоты (429)."""

import pytest

from espanol import telegram
from espanol.telegram import TelegramAPI, TelegramError


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


class FakeSession:
    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.calls = []

    def post(self, url, json=None, data=None, files=None, timeout=None):
        self.calls.append({"url": url, "json": json, "data": data, "files": files})
        return FakeResponse(self.bodies.pop(0))


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(telegram.time, "sleep", lambda s: None)


def api_with(bodies):
    api = TelegramAPI("TOKEN")
    api.session = FakeSession(bodies)
    return api


def test_send_poll_payload():
    api = api_with([{"ok": True, "result": {"message_id": 1}}])
    api.send_poll("@ch", "¿Qué?", ["a", "b"], 1, "<b>x</b>")
    call = api.session.calls[0]
    assert call["url"].endswith("/botTOKEN/sendPoll")
    assert call["json"]["type"] == "quiz" and call["json"]["correct_option_id"] == 1
    assert call["json"]["options"] == [{"text": "a"}, {"text": "b"}]
    assert call["json"]["explanation_parse_mode"] == "HTML"


def test_retry_after_429():
    api = api_with([
        {"ok": False, "error_code": 429, "parameters": {"retry_after": 1}},
        {"ok": True, "result": {"message_id": 2}},
    ])
    assert api.send_message("@ch", "<b>hola</b>") == {"message_id": 2}
    assert len(api.session.calls) == 2


def test_error_is_raised():
    api = api_with([{"ok": False, "error_code": 400, "description": "Bad Request: chat not found"}])
    with pytest.raises(TelegramError, match="chat not found"):
        api.send_message("@nope", "x")


def test_audio_is_multipart():
    api = api_with([{"ok": True, "result": {}}])
    api.send_audio("@ch", b"mp3", "a.mp3", title="Урок 1", silent=True)
    call = api.session.calls[0]
    assert "audio" in call["files"] and call["data"]["disable_notification"] == "true"


def test_token_required():
    with pytest.raises(TelegramError):
        TelegramAPI("")
