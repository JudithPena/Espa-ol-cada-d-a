"""Слова курса для бота на Cloudflare (bot/): личные повторения /repaso.

    python -m espanol bot-data                  # bot/data/words.json и озвучка в bot/public/audio/
    python -m espanol bot-data --no-audio       # без озвучки

Бот показывает только слова уже вышедших уроков: какие уроки вышли, он сам читает
из state/state.json на GitHub. Поэтому выгружаются слова всего курса, у каждого — id урока.
id слова — хеш его написания: он не меняется, когда уроки переставляют, и по нему бот
помнит, как каждый ученик знает слово.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import tts
from .course import Course, VocabItem
from .markup import plain

log = logging.getLogger(__name__)

VOICE = "f1"
RATE = "-10%"


def word_id(item: VocabItem) -> str:
    return hashlib.sha1(item.key.encode("utf-8")).hexdigest()[:10]


def _speech(item: VocabItem) -> list[tuple[str, str]]:
    segments = [(VOICE, item.speech)]
    if item.example:
        segments.append((VOICE, plain(item.example.es)))
    return segments


def _audio_name(item: VocabItem) -> str:
    voice = tts.DEFAULT_VOICES[VOICE]
    text = "|".join(t for _, t in _speech(item))
    return hashlib.sha1(f"{voice}|{RATE}|{text}".encode("utf-8")).hexdigest()[:16] + ".mp3"


def bot_words(course: Course) -> list[VocabItem]:
    """Слова для повторения в порядке курса, каждое один раз (там, где оно впервые появилось)."""
    seen: set[str] = set()
    words = []
    for lesson in course.lessons:
        for item in lesson.vocab:
            if item.srs and item.key not in seen:
                seen.add(item.key)
                words.append(item)
    return words


def word_record(item: VocabItem, audio: str = "") -> dict:
    return {
        "id": word_id(item),
        "es": plain(item.es),
        "ru": plain(item.ru),
        "pron": item.pron,
        "emoji": item.emoji,
        "ex": [plain(item.example.es), plain(item.example.ru)] if item.example else None,
        "lesson": item.lesson.id if item.lesson else "",
        "audio": audio,
    }


def export(course: Course, out: Path, audio: bool = True, cache: Path | None = None,
           workers: int = 6) -> dict:
    """Пишет out/data/words.json и озвучку в out/public/audio/. Готовые mp3 берутся из cache."""
    words = bot_words(course)
    audio_dir = out / "public" / "audio"
    if audio_dir.exists():
        shutil.rmtree(audio_dir)
    names: dict[str, str] = {}
    if audio and tts.available():
        cache = cache or out / ".audio-cache"
        cache.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True)
        todo = [item for item in words if not (cache / _audio_name(item)).exists()]
        log.info("озвучка: готово %d, синтезирую %d", len(words) - len(todo), len(todo))

        def speak(item: VocabItem) -> None:
            try:
                (cache / _audio_name(item)).write_bytes(tts.synthesize(_speech(item), rate=RATE))
            except tts.TTSError as exc:  # без озвучки карточка всё равно работает
                log.warning("нет озвучки для «%s»: %s", item.es, exc)

        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(speak, todo))
        for item in words:
            name = _audio_name(item)
            if (cache / name).exists():
                shutil.copyfile(cache / name, audio_dir / name)
                names[item.key] = name
    records = [word_record(item, names.get(item.key, "")) for item in words]
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("у двух слов совпал id — поменяйте длину хеша в botdata.word_id")
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "words.json").write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"words": len(records), "audio": len(names)}
