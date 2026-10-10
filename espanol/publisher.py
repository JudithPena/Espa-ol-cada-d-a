"""Публикация уроков в канал с сохранением прогресса.

Прогресс хранится в JSON-файле (state/state.json): какие уроки уже вышли и
сколько сообщений текущего урока отправлено. Если отправка оборвалась на
середине, следующий запуск продолжит с того же места без дублей.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from . import tts
from .course import Course, Lesson
from .markup import strip_tags
from .render import AudioMessage, Message, PollMessage, Renderer, TextMessage
from .telegram import TelegramAPI

log = logging.getLogger(__name__)


@dataclass
class State:
    path: Path
    published: list[dict] = field(default_factory=list)
    current: dict | None = None

    @classmethod
    def load(cls, path: Path) -> "State":
        if not path.exists():
            return cls(path)
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
        return cls(path, data.get("published", []), data.get("current"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"published": self.published, "current": self.current}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def published_ids(self) -> set[str]:
        return {p["id"] for p in self.published}

    def count_on_day(self, day: str, tz: ZoneInfo) -> int:
        n = 0
        for p in self.published:
            at = datetime.fromisoformat(p["at"]).astimezone(tz)
            n += at.date().isoformat() == day
        return n


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def describe(message: Message) -> str:
    """Текстовое представление сообщения для --dry-run и предпросмотра."""
    if isinstance(message, TextMessage):
        return strip_tags(message.html)
    if isinstance(message, PollMessage):
        lines = [f"📊 ОПРОС: {message.question}"]
        for i, option in enumerate(message.options):
            lines.append(f"   {'✅' if i == message.correct else '▫️'} {option}")
        if message.explanation:
            lines.append(f"   💡 {strip_tags(message.explanation)}")
        return "\n".join(lines)
    seconds = sum(len(t) for _, t in message.segments) // 12
    return f"🎧 АУДИО «{message.title}»: {len(message.segments)} фрагм., ~{seconds} c"


class Publisher:
    def __init__(self, course: Course, renderer: Renderer, api: TelegramAPI | None, chat_id: str,
                 state_path: Path, tz: str = "Europe/Moscow", posts_per_day: int = 1,
                 audio: bool = True, tts_rate: str = "-10%", voices: dict | None = None,
                 delay: float = 1.5, synth: Callable[..., bytes] | None = None):
        self.course = course
        self.renderer = renderer
        self.api = api
        self.chat_id = chat_id
        self.state_path = Path(state_path)
        self.tz = ZoneInfo(tz)
        self.posts_per_day = posts_per_day
        self.audio = audio
        self.tts_rate = tts_rate
        self.voices = voices or {}
        self.delay = delay
        self.synth = synth or tts.synthesize

    def state(self) -> State:
        return State.load(self.state_path)

    def next_lesson(self, state: State) -> tuple[Lesson | None, int]:
        if state.current:
            try:
                return self.course.lesson(state.current["id"]), int(state.current.get("sent", 0))
            except KeyError:
                log.warning("урок %s из state не найден — начинаю следующий", state.current["id"])
                state.current = None
        done = state.published_ids()
        for lesson in self.course.lessons:
            if lesson.id not in done:
                return lesson, 0
        return None, 0

    def publish_next(self, force: bool = False, dry_run: bool = False) -> str:
        state = self.state()
        lesson, start = self.next_lesson(state)
        if lesson is None:
            return "🎓 Курс полностью опубликован — новых уроков нет."
        today = datetime.now(self.tz).date().isoformat()
        if not force and not state.current and state.count_on_day(today, self.tz) >= self.posts_per_day:
            return f"Сегодня ({today}) уже опубликовано постов: {self.posts_per_day}. Пропускаю."

        messages = self.renderer.render(lesson)
        if dry_run:
            for i, message in enumerate(messages[start:], start + 1):
                print(f"\n——— сообщение {i}/{len(messages)} ———\n{describe(message)}")
            return f"[dry-run] урок {lesson.number} ({lesson.id}), сообщений: {len(messages)}"

        state.current = {"id": lesson.id, "sent": start}
        state.save()

        def on_sent(n: int) -> None:
            state.current = {"id": lesson.id, "sent": n}
            state.save()

        self.send(messages, self.chat_id, start=start, on_sent=on_sent, lesson=lesson)
        state.current = None
        state.published.append({"id": lesson.id, "at": now_utc().isoformat()})
        state.save()
        return f"✅ Опубликован урок {lesson.number}: {lesson.kind_label} · {lesson.title} ({lesson.id})"

    def send(self, messages: list[Message], chat_id: str, start: int = 0,
             on_sent: Callable[[int], None] | None = None, lesson: Lesson | None = None) -> None:
        if self.api is None:
            raise RuntimeError("не настроен Telegram API")
        for n in range(start, len(messages)):
            message = messages[n]
            if isinstance(message, TextMessage):
                self.api.send_message(chat_id, message.html, silent=message.silent)
            elif isinstance(message, PollMessage):
                self.api.send_poll(chat_id, message.question, message.options, message.correct,
                                   message.explanation, silent=message.silent)
            elif isinstance(message, AudioMessage):
                self._send_audio(chat_id, message, lesson)
            if on_sent:
                on_sent(n + 1)
            if n < len(messages) - 1:
                time.sleep(self.delay)

    def _send_audio(self, chat_id: str, message: AudioMessage, lesson: Lesson | None) -> None:
        if not self.audio:
            return
        try:
            mp3 = self.synth(message.segments, rate=self.tts_rate, pauses=message.pauses,
                             voices=self.voices)
        except Exception as exc:  # озвучка — бонус, урок публикуем и без неё
            log.warning("озвучка не удалась, пропускаю аудио: %s", exc)
            return
        name = f"espanol_{lesson.number:03d}.mp3" if lesson else "espanol.mp3"
        self.api.send_audio(chat_id, mp3, name, title=message.title, performer=self.course.title,
                            caption=message.caption, duration=tts.duration(mp3), silent=message.silent)
