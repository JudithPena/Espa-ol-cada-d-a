"""Урок одним постом-статьёй Telegram (Rich Messages, Bot API 10.1+).

Вместо нескольких сообщений урок уходит одной статьёй: обложка, заголовки,
карточки новых слов, аудио рядом с каждым диалогом, таблицы. Ответы и переводы
спрятаны в раскрывающиеся блоки <details>: каждый открывается отдельно, поэтому
ответы одного задания не открываются вместе с другим. Опросы остаются
отдельными сообщениями после статьи.

Картинки и аудио здесь только описываются (RichMedia), а рисуются
и синтезируются при отправке, в publisher.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from . import cards
from . import morphology as morph
from .course import Block, Lesson, VocabItem
from .markup import escape, plain, strip_tags, to_html
from .render import REFLEXIVE_BY_PERSON, Message, PollMessage, Renderer
from .srs import Pick

RICH_TEXT_LIMIT = 32768
RICH_BLOCK_LIMIT = 500
RICH_MEDIA_LIMIT = 50


@dataclass
class RichMedia:
    id: str                      # имя в ссылке tg://photo?id=… / tg://audio?id=…
    kind: str                    # photo | audio
    draw: Callable[[], bytes] | None = None             # картинка рисуется при отправке
    segments: list[tuple[str, str]] = field(default_factory=list)  # аудио — синтез при отправке
    title: str = ""
    pauses: bool = False


@dataclass
class RichMessage:
    html: str
    media: list[RichMedia]
    silent: bool = False


def paragraphs(html_text: str) -> str:
    """Абзацы <p>; одиночный перевод строки становится <br>."""
    parts = [p.strip() for p in html_text.split("\n\n") if p.strip()]
    return "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in parts)


def details(summary: str, body: str, is_open: bool = False) -> str:
    return f"<details{' open' if is_open else ''}><summary>{summary}</summary>{body}</details>"


def describe_rich(message: RichMessage) -> str:
    """Статья обычным текстом — для предпросмотра и --dry-run."""
    titles = {m.id: m.title for m in message.media}
    text = re.sub(r'<img src="tg://photo\?id=([\w-]+)"/>', r"\n🖼 [картинка \1]\n", message.html)
    text = re.sub(r'<audio src="tg://audio\?id=([\w-]+)"></audio>',
                  lambda m: f"▶️ [аудио «{titles.get(m.group(1), m.group(1))}»] ", text)
    text = re.sub(r"<summary>", "▸ ", text)
    text = re.sub(r"<li>", "• ", text)
    text = re.sub(r"<br>|</(p|h2|h3|li|summary|figure|tr|blockquote)>", "\n", text)
    text = re.sub(r"</td>", " | ", text)
    text = re.sub(r"<(h2|h3)>", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", strip_tags(text)).strip()


def drop_media(html_text: str, media_id: str) -> str:
    """Убирает из статьи картинку или аудио, которые не удалось подготовить."""
    ref = re.escape(f'?id={media_id}"')
    html_text = re.sub(rf'<figure>(?:(?!</figure>).)*?{ref}.*?</figure>', "", html_text)
    html_text = re.sub(rf'<img src="tg://photo{ref}/>', "", html_text)
    return html_text.replace("<tg-slideshow></tg-slideshow>", "")


class RichRenderer:
    def __init__(self, renderer: Renderer, images: bool | None = None):
        self.r = renderer
        self.images = cards.available() if images is None else images

    def render(self, lesson: Lesson) -> list[Message]:
        """Статья + опросы (опросы те же, что в обычном формате)."""
        media: list[RichMedia] = []
        out: list[str] = []
        unit = lesson.unit
        if self.images:
            media.append(RichMedia("cover", "photo", draw=lambda: cards.cover(
                f"{strip_tags(self.r._label('lesson', lesson))} {lesson.number} · {lesson.level} · "
                f"{strip_tags(self.r._label('unit', lesson))} {unit.number}",
                plain(lesson.title), plain(unit.title), lesson.kind_emoji)))
            out.append('<figure><img src="tg://photo?id=cover"/></figure>')
        out.append(f"<p>🇪🇸 <b>{self.r._label('lesson', lesson)} {lesson.number}</b> · "
                   f"{escape(lesson.level)} · {self.r._label('unit', lesson)} {unit.number}. "
                   f"{to_html(unit.title)}</p>")
        out.append(f"<h2>{lesson.kind_emoji} {self.r.kind_label(lesson)} · {to_html(lesson.title)}</h2>")
        if unit.goals and unit.lessons[0] is lesson:
            out.append("<h3>🎯 В этой теме вы научитесь:</h3>"
                       + "<ul>" + "".join(f"<li>{to_html(g)}</li>" for g in unit.goals) + "</ul>")

        blocks = list(lesson.blocks)
        if lesson.vocab and not any(b.type == "words" for b in blocks):
            blocks.insert(1 if blocks and blocks[0].type == "text" else 0, Block("words", None))
        voices: dict[str, str] = {}
        for block in blocks:
            out.append(self._block(block, lesson, media, voices))

        picks = self.r.schedule.picks_for(lesson)
        polls = [m for m in self.r.render(lesson) if isinstance(m, PollMessage)]
        if lesson.kind == "review":
            out.append(self._review(picks))
        elif picks and lesson.kind not in ("quiz", "final"):
            out.append(self._recall(picks, lesson))
        if polls and lesson.kind in ("quiz", "final"):
            out.append(f"<p>👇 <b>Вопросов: {len(polls)}.</b> Отвечайте по памяти и не подглядывайте, "
                       "потому что именно попытка вспомнить и закрепляет материал.</p>")
        elif polls:
            out.append(f"<p>{self.r._label('polls', lesson)}</p>")
        out.append(f"<p>{self.r._footer(lesson)}</p>")
        return [RichMessage("".join(p for p in out if p), media), *polls]

    # ------------------------------------------------------------ блоки

    def _audio(self, lesson: Lesson, media: list[RichMedia], segments: list[tuple[str, str]],
               name: str, caption: str = "", pauses: bool = False) -> str:
        """Аудиоплеер прямо в статье; name — часть названия трека («Урок 8 · Утром»)."""
        if not lesson.audio or not segments:
            return ""
        media_id = f"a{sum(m.kind == 'audio' for m in media) + 1}"
        title = f"{strip_tags(self.r._label('lesson', lesson))} {lesson.number} · {name}"
        media.append(RichMedia(media_id, "audio", segments=segments, title=title, pauses=pauses))
        caption = caption or strip_tags(self.r._label("audio", lesson))
        return (f'<figure><audio src="tg://audio?id={media_id}"></audio>'
                f"<figcaption>{caption}</figcaption></figure>")

    def _block(self, block: Block, lesson: Lesson, media: list[RichMedia], voices: dict[str, str]) -> str:
        t, d = block.type, block.data
        if t == "text":
            return paragraphs(to_html(d))
        if t == "header":
            return f"<h3>{to_html(d)}</h3>"
        if t == "rule":
            return f"<blockquote>📌 {to_html(d).replace(chr(10), '<br>')}</blockquote>"
        if t in ("tip", "note", "culture"):
            icon = {"tip": "💡", "note": "📝", "culture": "🌍"}[t]
            return paragraphs(f"{icon} {to_html(d)}")
        if t == "latam":
            return paragraphs(f"🌎 <b>В Латинской Америке:</b> {to_html(d)}")
        if t == "task":
            return paragraphs(f"{self.r._label('task', lesson)} {to_html(d)}")
        if t in ("cando", "list"):
            head = "<h3>✅ Теперь вы умеете:</h3>" if t == "cando" else ""
            return head + "<ul>" + "".join(f"<li>{to_html(s)}</li>" for s in d) + "</ul>"
        if t == "words":
            return self._words(lesson, media)
        if t == "examples":
            return self._examples(d, lesson, media)
        if t == "table":
            title = f"<p><b>{to_html(d['title'])}</b></p>" if d.get("title") else ""
            rows = "".join("<tr>" + "".join(f"<td>{to_html(c)}</td>" for c in row) + "</tr>"
                           for row in d["rows"])
            return f"{title}<table bordered striped>{rows}</table>"
        if t == "conjugation":
            return self._conjugation(d, lesson, media)
        if t == "exercise":
            title = d.get("title") or strip_tags(self.r._label("exercise", lesson))
            items = []
            for n, (q, a) in enumerate(d["items"], 1):
                question = f"{n}. {to_html(q)}"
                items.append(details(question, f"<p>{to_html(a)}</p>") if a else f"<p>{question}</p>")
            return f"<h3>✍️ {to_html(title)}</h3>" + "".join(items)
        if t == "dialogue":
            return self._dialogue(d, lesson, media, voices)
        if t == "reading":
            title = f"<h3>📖 {to_html(d['title'])}</h3>" if d.get("title") else ""
            text = paragraphs(to_html(d["text"]))
            audio = self._audio(lesson, media, [("f1", plain(d["text"]))], plain(d.get("title") or lesson.title))
            translation = ""
            if d["translation"]:
                translation = details(strip_tags(self.r._label("translation", lesson)),
                                      paragraphs(to_html(d["translation"])))
            return title + text + audio + translation
        raise ValueError(t)  # pragma: no cover

    def _words(self, lesson: Lesson, media: list[RichMedia]) -> str:
        out = [f"<h3>{strip_tags(self.r._label('new_words', lesson))}</h3>"]
        if self.images and lesson.vocab:
            ids = []
            for n, item in enumerate(lesson.vocab, 1):
                ids.append(f"w{n}")
                media.append(RichMedia(f"w{n}", "photo", draw=_card(item)))
            imgs = "".join(f'<img src="tg://photo?id={i}"/>' for i in ids)
            out.append(f"<tg-slideshow>{imgs}</tg-slideshow>" if len(ids) > 1 else f"<figure>{imgs}</figure>")
        items, segments = [], []
        for item in lesson.vocab:
            line = f"{item.emoji or '▫️'} <b>{escape(item.es)}</b>"
            if item.pron:
                line += f" [{escape(item.pron)}]"
            line += f" — {to_html(item.ru)}"
            if item.example:
                line += f"<br><i>{to_html(item.example.es)}</i> — {to_html(item.example.ru)}"
            if item.note:
                line += f"<br>💡 {to_html(item.note)}"
            items.append(f"<li>{line}</li>")
            segments.append(("f1", item.speech))
            if item.example:
                segments.append(("f1", plain(item.example.es)))
        out.append("<ul>" + "".join(items) + "</ul>")
        out.append(self._audio(lesson, media, segments, strip_tags(self.r._label("new_words", lesson))[2:],
                               pauses=lesson.kind in ("vocab", "phonetics")))
        return "".join(out)

    def _examples(self, d: dict, lesson: Lesson, media: list[RichMedia]) -> str:
        out = [f"<p><b>{to_html(d['title'])}</b></p>"] if d.get("title") else []
        plain_items = []
        for ex in d["items"]:
            es, ru = to_html(ex.es), to_html(ex.ru)
            if d.get("hide") == "ru":
                out.append(details(f"<i>{es}</i>", f"<p>{ru}</p>"))
            elif d.get("hide") == "es":
                out.append(details(ru, f"<p><i>{es}</i></p>"))
            else:
                plain_items.append(f"<li><i>{es}</i> — {ru}</li>")
        if plain_items:
            out.append("<ul>" + "".join(plain_items) + "</ul>")
        out.append(self._audio(lesson, media, [("f1", plain(ex.es)) for ex in d["items"]],
                               plain(d.get("title") or lesson.title)))
        return "".join(out)

    def _conjugation(self, d: dict, lesson: Lesson, media: list[RichMedia]) -> str:
        verb = d["verb"]
        title = d.get("title") or verb + (f" — {d['ru']}" if d.get("ru") else "")
        _, _, stem, reflexive = morph.split_verb(verb)
        rows, segments = [], []
        for n, (person, form) in enumerate(zip(morph.PERSONS, d["forms"])):
            shown = escape(form)
            if d.get("highlight", True):
                if stem and form.startswith(stem) and len(form) > len(stem):
                    shown = f"{escape(form[:len(stem)])}<b>{escape(form[len(stem):])}</b>"
                else:
                    shown = f"<b>{escape(form)}</b>"
            pronoun = f" {REFLEXIVE_BY_PERSON[n]}" if reflexive else ""
            rows.append(f"<tr><td>{escape(person)}{pronoun}</td><td>{shown}</td></tr>")
            segments.append(("f1", f"{person.split('/')[0]}{pronoun} {form}"))
        audio = self._audio(lesson, media, segments, plain(verb))
        return f"<p><b>{to_html(title)}</b></p><table bordered striped>{''.join(rows)}</table>{audio}"

    def _dialogue(self, d: dict, lesson: Lesson, media: list[RichMedia], voices: dict[str, str]) -> str:
        out = [f"<h3>💬 {to_html(d['title'])}</h3>"] if d.get("title") else []
        lines, translation, segments = [], [], []
        for speaker, es, ru in d["lines"]:
            lines.append(f"<p><b>{escape(speaker)}:</b> {to_html(es)}</p>")
            if ru:
                translation.append(f"<p><b>{escape(speaker)}:</b> {to_html(ru)}</p>")
            segments.append((self.r._voice(speaker, voices, d["voices"]), plain(es)))
        audio = self._audio(lesson, media, segments, plain(d.get("title") or lesson.title))
        if d.get("hidden"):  # аудирование: сначала слушаем, текст спрятан
            out.append(audio)
            out.append(details(strip_tags(self.r._label("hidden_text", lesson)), "".join(lines)))
        else:
            out += lines + [audio]
        if translation:
            out.append(details(strip_tags(self.r._label("translation", lesson)), "".join(translation)))
        return "".join(out)

    # ------------------------------------------------------------ повторение

    @staticmethod
    def _recall_item(pick: Pick) -> str:
        es, ru = escape(pick.item.es), to_html(pick.item.ru)
        if pick.production:
            return details(ru, f"<p><i>{es}</i></p>")
        return details(f"<i>{es}</i>", f"<p>{ru}</p>")

    def _recall(self, picks: list[Pick], lesson: Lesson) -> str:
        label = strip_tags(self.r._label("recall", lesson))
        head = label.split(" (")[0]
        hint = "<p>Нажмите на строку, чтобы проверить себя.</p>" if head != label else ""
        return f"<h3>{head}</h3>{hint}" + "".join(self._recall_item(p) for p in picks)

    def _review(self, picks: list[Pick]) -> str:
        if not picks:
            return ""
        recognise = [p for p in picks if not p.production]
        produce = [p for p in picks if p.production]
        out = []
        if recognise:
            out.append("<h3>1. Узнайте слово и переведите его на русский</h3>"
                       + "".join(self._recall_item(p) for p in recognise))
        if produce:
            out.append(f"<h3>{2 if recognise else 1}. Вспомните по-испански</h3>"
                       + "".join(self._recall_item(p) for p in produce))
        examples = [p.item.example for p in picks if p.item.example][:6]
        if examples:
            out.append("<h3>Слова в контексте</h3><p>Прочитайте примеры вслух и переведите их.</p>"
                       + "".join(details(f"<i>{to_html(e.es)}</i>", f"<p>{to_html(e.ru)}</p>")
                                 for e in examples))
        return "".join(out)


def _card(item: VocabItem) -> Callable[[], bytes]:
    return lambda: cards.word_card(item.es, plain(item.ru), item.emoji, item.pron)


def rich_problems(message: RichMessage) -> list[str]:
    """Проверка лимитов Rich Messages и корректности вложенности тегов."""
    from html.parser import HTMLParser

    problems = []
    text = strip_tags(message.html)
    if len(text) > RICH_TEXT_LIMIT:
        problems.append(f"статья длиннее {RICH_TEXT_LIMIT} символов: {len(text)}")
    blocks = len(re.findall(r"<(p|h[1-6]|li|tr|details|blockquote|figure|table|ul|ol|tg-slideshow)[ >]",
                            message.html))
    if blocks > RICH_BLOCK_LIMIT:
        problems.append(f"блоков больше {RICH_BLOCK_LIMIT}: {blocks}")
    if len(message.media) > RICH_MEDIA_LIMIT:
        problems.append(f"медиа больше {RICH_MEDIA_LIMIT}: {len(message.media)}")
    for m in message.media:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", m.id):
            problems.append(f"недопустимый id медиа: {m.id!r}")
        if f"?id={m.id}\"" not in message.html:
            problems.append(f"медиа {m.id} не используется в тексте")

    class Checker(HTMLParser):
        VOID = {"img", "br", "hr"}

        def __init__(self):
            super().__init__()
            self.stack: list[str] = []

        def handle_starttag(self, tag, attrs):
            if tag not in self.VOID:
                self.stack.append(tag)

        def handle_startendtag(self, tag, attrs):
            pass

        def handle_endtag(self, tag):
            if not self.stack or self.stack[-1] != tag:
                problems.append(f"неправильная вложенность: </{tag}> при {self.stack[-3:]}")
            else:
                self.stack.pop()

    checker = Checker()
    checker.feed(message.html)
    checker.close()
    if checker.stack:
        problems.append(f"не закрыты теги: {checker.stack}")
    return problems
