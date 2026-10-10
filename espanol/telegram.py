"""Минимальный клиент Telegram Bot API (только то, что нужно для канала)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

log = logging.getLogger(__name__)


class TelegramError(Exception):
    pass


class TelegramAPI:
    def __init__(self, token: str, base_url: str = "https://api.telegram.org",
                 timeout: float = 60, retries: int = 5):
        if not token:
            raise TelegramError("не задан TELEGRAM_BOT_TOKEN")
        self.url = f"{base_url}/bot{token}"
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()

    def call(self, method: str, payload: dict[str, Any] | None = None,
             files: dict[str, tuple] | None = None) -> Any:
        payload = payload or {}
        for attempt in range(1, self.retries + 1):
            try:
                if files:
                    data = {k: json.dumps(v) if isinstance(v, (dict, list, bool)) else v
                            for k, v in payload.items()}
                    resp = self.session.post(f"{self.url}/{method}", data=data, files=files,
                                             timeout=self.timeout)
                else:
                    resp = self.session.post(f"{self.url}/{method}", json=payload, timeout=self.timeout)
                body = resp.json()
            except (requests.RequestException, ValueError) as exc:
                if attempt == self.retries:
                    raise TelegramError(f"{method}: сеть недоступна: {exc}") from exc
                time.sleep(2 ** attempt)
                continue
            if body.get("ok"):
                return body["result"]
            code = body.get("error_code")
            if code == 429:
                wait = body.get("parameters", {}).get("retry_after", 5)
                log.warning("Telegram просит подождать %s c", wait)
                time.sleep(wait + 1)
                continue
            if code and code >= 500 and attempt < self.retries:
                time.sleep(2 ** attempt)
                continue
            raise TelegramError(f"{method}: {code} {body.get('description')}")
        raise TelegramError(f"{method}: не удалось после {self.retries} попыток")

    def get_me(self) -> dict:
        return self.call("getMe")

    def send_message(self, chat_id: str, html: str, silent: bool = False) -> dict:
        return self.call("sendMessage", {
            "chat_id": chat_id,
            "text": html,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
            "disable_notification": silent,
        })

    def send_poll(self, chat_id: str, question: str, options: list[str], correct: int,
                  explanation: str = "", silent: bool = True) -> dict:
        payload = {
            "chat_id": chat_id,
            "question": question,
            "options": [{"text": o} for o in options],
            "type": "quiz",
            "correct_option_id": correct,
            "is_anonymous": True,
            "disable_notification": silent,
        }
        if explanation:
            payload["explanation"] = explanation
            payload["explanation_parse_mode"] = "HTML"
        return self.call("sendPoll", payload)

    def send_audio(self, chat_id: str, audio: bytes, filename: str, title: str,
                   performer: str = "", caption: str = "", duration: int | None = None,
                   silent: bool = True) -> dict:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "title": title,
            "performer": performer,
            "caption": caption,
            "parse_mode": "HTML",
            "disable_notification": silent,
        }
        if duration:
            payload["duration"] = duration
        return self.call("sendAudio", payload, files={"audio": (filename, audio, "audio/mpeg")})
