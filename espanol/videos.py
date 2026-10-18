"""Рубрика «Разбор видео»: отдельные посты-статьи, которые опираются на курс.

Разборы лежат в content/videos/NN_имя.yaml и в нумерацию курса не входят:
у них свои номера (№1, №2…), а прогресс публикации они не меняют.
Каждый разбор опирается на уроки 0…after — те, что уже вышли в канал,
когда разбор публикуется. Слова из этих уроков в разборе не разбираем,
а все остальные слова из видео разбираем. Номера уроков курса в посте
не указываем.

Курс под разборы не меняется: разборы подстраиваются под курс, а не наоборот.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import cards
from .course import ContentError, Course, Lesson, Unit, VocabItem, parse_lesson
from .lexicon import Lexicon, generated_forms, lesson_texts
from .markup import checkable, escape, plain, strip_tags, to_html
from .render import Message, PollMessage, Renderer, poll_problems
from .rich import RichMedia, RichMessage, RichRenderer, details, paragraphs, rich_problems
from .tokens import spanish_words

VIDEO_REF = re.compile(r"(?:video|видео):(\w+)$", re.I)


@dataclass
class Video:
    number: int
    id: str
    title: str
    url: str
    after: int            # последний вышедший урок курса, на который опирается разбор
    transcript: str       # полный текст видео в оригинале
    translation: str      # перевод (в посте спрятан)
    lesson: Lesson        # слова, блоки и опросы в формате урока
    source: str

    @property
    def label(self) -> str:
        return f"Разбор видео №{self.number}"


def is_video_ref(ref: str) -> bool:
    return bool(VIDEO_REF.match(str(ref)))


def load_videos(content_dir: str | Path, course: Course) -> list[Video]:
    videos: list[Video] = []
    unit = Unit(id="video", number=0, level="A1", title="Разбор видео", goals=[])
    for path in sorted((Path(content_dir) / "videos").glob("*.yaml")):
        where = f"videos/{path.name}"
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ContentError(f"{where}: ошибка YAML: {exc}") from exc
        prefix = path.stem.split("_", 1)[0]
        if not prefix.isdigit():
            raise ContentError(f"{where}: имя файла должно начинаться с номера разбора (01_…)")
        for key in ("title", "url", "after", "transcript", "translation"):
            if key not in raw:
                raise ContentError(f"{where}: нет поля {key}")
        after = int(raw["after"])
        if not 0 <= after < len(course.lessons):
            raise ContentError(f"{where}: after = {after}, а уроки курса — от 0 до {len(course.lessons) - 1}")
        local_id = str(raw.get("id") or path.stem.split("_", 1)[-1])
        lesson = parse_lesson({
            "id": local_id, "kind": "video", "title": raw["title"], "level": raw.get("level"),
            "vocab": raw.get("vocab"), "blocks": raw.get("blocks"), "quiz": raw.get("quiz"),
            "forms": raw.get("forms"), "allow": raw.get("allow"), "audio": raw.get("audio", True),
        }, unit, where)
        lesson.index = after  # подписи и проверка слов — как в уроке after
        videos.append(Video(
            number=int(prefix), id=local_id, title=str(raw["title"]).strip(), url=str(raw["url"]).strip(),
            after=after, transcript=str(raw["transcript"]).strip(),
            translation=str(raw["translation"]).strip(), lesson=lesson, source=str(path),
        ))
    return videos


def find_video(videos: list[Video], ref: str) -> Video:
    m = VIDEO_REF.match(str(ref))
    key = m.group(1) if m else str(ref)
    for video in videos:
        if key == video.id or (key.isdigit() and int(key) == video.number):
            return video
    raise KeyError(f"нет разбора «{ref}» (есть: {', '.join(f'video:{v.number}' for v in videos) or 'ни одного'})")


# ---------------------------------------------------------------- слова


class VideoWords:
    """Какие слова разбора ученик уже знает по урокам 0…after."""

    def __init__(self, lexicon: Lexicon, video: Video):
        self.lexicon = lexicon
        self.video = video
        after = video.after
        self.known = set(lexicon.known_at[after])
        features = lexicon.features_at[after]
        for item in video.lesson.vocab:
            self.known |= item.base_forms() | generated_forms(item, features)
        self.known |= set(video.lesson.forms)
        self.allow = {a.lower() for a in video.lesson.allow}

    def is_known(self, word: str) -> bool:
        low = word.lower()
        return (word in self.lexicon.names or low in self.known or low in self.allow
                or low in self.lexicon.course.meta_words)

    def passed_lesson(self, item: VocabItem) -> Lesson | None:
        """Урок из уже вышедших, где это слово уже проходили (тогда его не разбираем)."""
        after = self.video.after
        for it in self.lexicon.items:
            if it.lesson.index <= after and (it.key == item.key or set(it.cores) & set(item.cores)):
                return it.lesson
        words = spanish_words(item.es)
        if len(words) == 1:
            lesson = self.lexicon.first_seen.get(words[0].lower())
            if lesson and lesson.index <= after:
                return lesson
        return None


def video_texts(video: Video) -> list[tuple[str, str]]:
    return [("название", video.title), ("текст видео", video.transcript), *lesson_texts(video.lesson)]


def check_video(video: Video, lexicon: Lexicon) -> list[str]:
    where = f"{video.label} ({video.id})"
    words = VideoWords(lexicon, video)
    problems: list[str] = []
    unknown: dict[str, str] = {}
    for place, text in video_texts(video):
        for word in spanish_words(checkable(text)):
            if not words.is_known(word):
                unknown.setdefault(word, f"{place}: «{plain(text)[:50]}»")
    for word, place in unknown.items():
        later = lexicon.first_seen.get(word.lower())
        hint = f", будет в уроке {later.number}" if later else ", в курсе его нет"
        problems.append(f"{where}: слово «{word}» не пройдено в уроках 0–{video.after}{hint} — "
                        f"разберите его в vocab ({place})")
    for item in video.lesson.vocab:
        passed = words.passed_lesson(item)
        if passed:
            problems.append(f"{where}: «{item.es}» уже пройдено в уроке {passed.number} — "
                            "по правилам рубрики его не разбираем")
    if not re.match(r"https?://", video.url):
        problems.append(f"{where}: url должен быть ссылкой на видео")
    return problems


# ---------------------------------------------------------------- пост


class VideoRenderer(RichRenderer):
    """Разбор видео одной статьёй: обложка, ссылка, слова, текст видео с переводом, пояснения, опросы."""

    def __init__(self, renderer: Renderer, lexicon: Lexicon, images: bool | None = None):
        super().__init__(renderer, images)
        self.lexicon = lexicon
        self.video: Video | None = None

    def render_video(self, video: Video) -> list[Message]:
        self.video = video
        lesson = video.lesson
        media: list[RichMedia] = []
        out: list[str] = []
        if self.images:
            media.append(RichMedia("cover", "photo", draw=lambda: cards.cover(
                f"{video.label} · {lesson.level}", plain(video.title), f"После урока {video.after}",
                lesson.kind_emoji)))
            out.append('<figure><img src="tg://photo?id=cover"/></figure>')
        out.append(f"<p>{lesson.kind_emoji} <b>{escape(video.label)}</b> · {escape(lesson.level)} · "
                   f"после урока {video.after}</p>")
        out.append(f"<h2>{to_html(video.title)}</h2>")
        out.append(f"<p>👉 <b>Видео:</b> {to_html(video.url)}</p>")

        blocks = list(lesson.blocks)
        voices: dict[str, str] = {}
        while blocks and blocks[0].type == "text":
            out.append(self._block(blocks.pop(0), lesson, media, voices))
        if lesson.vocab:
            out.append(self._words(lesson, media))
        # Флаг у перевода не ставим: в рубрике просто «Перевод».
        out.append("<h3>📜 Текст видео</h3>" + paragraphs(to_html(video.transcript))
                   + details("🔤 <b>Перевод</b>", paragraphs(to_html(video.translation))))
        for block in blocks:
            out.append(self._block(block, lesson, media, voices))

        polls = [PollMessage(p.question, p.options, p.correct, p.explanation)
                 for p in (self.r._manual_poll(lesson, i) for i in range(len(lesson.quiz)))]
        if polls:
            out.append(f"<p>{self.r._label('polls', lesson)}</p>")
        out.append(f"<p>#{lesson.kind_tag} #{lesson.level}</p>")
        return [RichMessage("".join(p for p in out if p), media), *polls]

    def _audio(self, lesson: Lesson, media: list[RichMedia], segments: list[tuple[str, str]],
               name: str, caption: str = "", pauses: bool = False) -> str:
        if not lesson.audio or not segments or not self.video:
            return ""
        media_id = f"a{sum(m.kind == 'audio' for m in media) + 1}"
        media.append(RichMedia(media_id, "audio", segments=segments,
                               title=f"{self.video.label} · {name}", pauses=pauses))
        caption = caption or strip_tags(self.r._label("audio", lesson))
        return (f'<figure><audio src="tg://audio?id={media_id}"></audio>'
                f"<figcaption>{caption}</figcaption></figure>")


def video_problems(videos: list[Video], lexicon: Lexicon, renderer: Renderer) -> list[str]:
    problems: list[str] = []
    numbers: set[int] = set()
    for video in videos:
        where = f"{video.label} ({video.id})"
        if video.number in numbers:
            problems.append(f"{where}: номер {video.number} уже занят другим разбором")
        numbers.add(video.number)
        problems += check_video(video, lexicon)
        messages = VideoRenderer(renderer, lexicon, images=True).render_video(video)
        problems += [f"{where}, статья: {p}" for p in rich_problems(messages[0])]
        for m in messages[1:]:
            if isinstance(m, PollMessage):
                problems += [f"{where}: {p}" for p in poll_problems(m)]
    return problems
