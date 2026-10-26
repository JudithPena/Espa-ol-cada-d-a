"""Слова курса для бота на Cloudflare (bot/): личные повторения /repaso.

    python -m espanol bot-data                  # bot/data/words.json и озвучка в bot/public/audio/
    python -m espanol bot-data --no-audio       # без озвучки

Там же — личная колода автора «Мои слова» (/palabras): bot/data/mywords.json, см. espanol/mywords.py.

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
from .mywords import Word, record
from .wordcards import WordCard, render_card

log = logging.getLogger(__name__)

VOICE = "f1"
RATE = "-10%"
ARTIST = "Español cada día"
VOICES = {**tts.DEFAULT_VOICES, "en": "en-US-AriaNeural"}  # en — английские слова в «Моих словах»


def word_id(item: VocabItem) -> str:
    return hashlib.sha1(item.key.encode("utf-8")).hexdigest()[:10]


Speech = list[tuple[str, str]]  # (голос, текст)


def _speech(item: VocabItem) -> Speech:
    segments = [(VOICE, item.speech)]
    if item.example:
        segments.append((VOICE, plain(item.example.es)))
    return segments


def _deck_speech(word: Word) -> Speech:
    voice = VOICE if word.lang == "es" else "en"
    segments = [(voice, word.word)]
    if word.examples:
        segments.append((voice, plain(word.examples[0][0])))
    return segments


def _audio_name(segments: Speech) -> str:
    voice = VOICES[segments[0][0]]
    text = "|".join(t for _, t in segments)
    return hashlib.sha1(f"{voice}|{RATE}|{text}".encode("utf-8")).hexdigest()[:16] + ".mp3"


def id3_tag(title: str, artist: str) -> bytes:
    """Тег ID3v2.3 с названием и исполнителем: по нему Telegram подписывает аудио словом,
    а не именем файла."""
    def frame(name: str, text: str) -> bytes:
        data = b"\x01" + "\ufeff".encode("utf-16-le") + text.encode("utf-16-le")
        return name.encode() + len(data).to_bytes(4, "big") + b"\x00\x00" + data

    body = frame("TIT2", title) + frame("TPE1", artist)
    size = len(body)
    syncsafe = bytes([(size >> 21) & 0x7F, (size >> 14) & 0x7F, (size >> 7) & 0x7F, size & 0x7F])
    return b"ID3\x03\x00\x00" + syncsafe + body


def _public_name(segments: Speech, title: str) -> str:
    """Имя файла на сайте бота: новое при каждой смене слова или тега, чтобы Telegram не брал старый файл."""
    return hashlib.sha1(f"id3|{_audio_name(segments)}|{title}".encode("utf-8")).hexdigest()[:16] + ".mp3"


def _write_audio(entries: list[tuple[str, Speech, str]], audio_dir: Path, cache: Path,
                 workers: int) -> dict[str, str]:
    """Озвучка (ключ, фрагменты, название) → {ключ: имя mp3 в audio_dir}. Готовые mp3 берутся из cache."""
    todo = {_audio_name(seg): seg for _, seg, _ in entries if not (cache / _audio_name(seg)).exists()}
    log.info("озвучка: готово %d, синтезирую %d", len(entries) - len(todo), len(todo))

    def speak(segments: Speech) -> None:
        try:
            (cache / _audio_name(segments)).write_bytes(tts.synthesize(segments, rate=RATE, voices=VOICES))
        except tts.TTSError as exc:  # без озвучки карточка всё равно работает
            log.warning("нет озвучки для «%s»: %s", segments[0][1], exc)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(speak, todo.values()))
    names = {}
    for key, segments, title in entries:
        name = _audio_name(segments)
        if (cache / name).exists():
            public = _public_name(segments, title)
            (audio_dir / public).write_bytes(id3_tag(title, ARTIST) + (cache / name).read_bytes())
            names[key] = public
    return names


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


def word_record(item: VocabItem, audio: str = "", card: WordCard | None = None) -> dict:
    return {
        "id": word_id(item),
        "word": plain(item.es),  # общие поля с «Моими словами»: word, ipa, card — для занятия в боте
        "ipa": f"[{item.pron}]" if item.pron else "",
        "card": render_card(item, card),
        "lang": "es",
        "es": plain(item.es),
        "ru": plain(item.ru),
        "pron": item.pron,
        "emoji": item.emoji,
        "ex": [plain(item.example.es), plain(item.example.ru)] if item.example else None,
        "lesson": item.lesson.id if item.lesson else "",
        "audio": audio,
    }


def export(course: Course, out: Path, audio: bool = True, cache: Path | None = None,
           workers: int = 6, deck: list[Word] | None = None, cards: dict[str, WordCard] | None = None) -> dict:
    """Пишет out/data/words.json (слова курса), out/data/mywords.json («Мои слова»)
    и озвучку в out/public/audio/. Готовые mp3 берутся из cache."""
    words = bot_words(course)
    deck = deck or []
    audio_dir = out / "public" / "audio"
    if audio_dir.exists():
        shutil.rmtree(audio_dir)
    names: dict[str, str] = {}
    if audio and tts.available():
        cache = cache or out / ".audio-cache"
        cache.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True)
        names = _write_audio(
            [(item.key, _speech(item), plain(item.es)) for item in words]
            + [(f"deck:{w.id}", _deck_speech(w), w.word) for w in deck],
            audio_dir, cache, workers)
    cards = cards or {}
    records = [word_record(item, names.get(item.key, ""), cards.get(item.key)) for item in words]
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("у двух слов совпал id — поменяйте длину хеша в botdata.word_id")
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "words.json").write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    mine = [record(w, names.get(f"deck:{w.id}", "")) for w in deck]
    (out / "data" / "mywords.json").write_text(json.dumps(mine, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"words": len(records), "audio": len(names), "deck": len(mine)}
