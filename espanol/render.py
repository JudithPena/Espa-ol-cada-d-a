"""Сборка урока в сообщения Telegram: текст (HTML), аудио и опросы."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from . import morphology as morph
from .course import Block, Course, Lesson, VocabItem
from .lexicon import Lexicon
from .markup import escape, plain, strip_tags, to_html, visible_len
from .quizgen import MAX_EXPLANATION, Poll, vocab_poll
from .srs import Pick, Schedule

TEXT_LIMIT = 3800  # у Telegram 4096, оставляем запас
REFLEXIVE_BY_PERSON = ("me", "te", "se", "nos", "os", "se")

# Подписи постов: (по-русски, по-испански). Испанский вариант включается сам,
# как только все его слова пройдены, — так язык постов постепенно становится испанским.
LABELS = {
    "new_words": ("🆕 <b>Новые слова</b>", "🆕 <b>Palabras nuevas</b>"),
    "recall": ("🔁 <b>Вспомним</b> (нажмите на скрытый текст, чтобы проверить себя)", "🔁 <b>Repaso</b>"),
    "translation": ("🇷🇺 <b>Перевод</b>", "🇷🇺 <b>Traducción</b>"),
    "task": ("✍️ <b>Задание:</b>", "✍️ <b>Tarea:</b>"),
    "audio": ("🎧 Слушайте и повторяйте вслух за диктором.", "🎧 Escucha y repite."),
    "hidden_text": ("📝 <b>Текст</b> (откройте после прослушивания):", "📝 <b>Texto</b>"),
    "exercise": ("Проверьте себя", "Responde"),
    "polls": ("👇 <b>Проверьте себя</b> в опросах ниже.", "👇 <b>Responde</b> a las preguntas."),
    "lesson": ("Урок", "Lección"),
    "unit": ("Тема", "Tema"),
}

# Испанские названия типов постов — включаются так же, когда слова пройдены.
KIND_ES = {
    "vocab": "Vocabulario",
    "grammar": "Gramática",
    "dialogue": "Diálogo",
    "listening": "Escucha",
    "reading": "Lectura",
    "practice": "Práctica",
    "quiz": "Test",
    "review": "Repaso",
    "final": "Examen",
    "finale": "Fin",
}


@dataclass
class TextMessage:
    html: str
    silent: bool = False


@dataclass
class PollMessage:
    question: str
    options: list[str]
    correct: int
    explanation: str = ""
    silent: bool = True


@dataclass
class AudioMessage:
    segments: list[tuple[str, str]]  # (голос: f1/f2/m1/m2, текст)
    title: str
    caption: str = ""
    silent: bool = True
    pauses: bool = False  # паузы для повторения за диктором


Message = TextMessage | PollMessage | AudioMessage


@dataclass
class _Out:
    parts: list[str] = field(default_factory=list)
    audio: list[tuple[str, str]] = field(default_factory=list)


class Renderer:
    def __init__(self, course: Course, lexicon: Lexicon | None = None,
                 schedule: Schedule | None = None):
        self.course = course
        self.lexicon = lexicon or Lexicon(course)
        self.schedule = schedule or Schedule(course, self.lexicon)

    # ------------------------------------------------------------ публичное

    def render(self, lesson: Lesson) -> list[Message]:
        out = _Out()
        unit = lesson.unit
        if unit.goals and unit.lessons[0] is lesson:
            out.parts.append("\n".join(["🎯 <b>В этой теме вы научитесь:</b>"]
                                        + [f"• {to_html(g)}" for g in unit.goals]))
        blocks = list(lesson.blocks)
        if lesson.vocab and not any(b.type == "words" for b in blocks):
            blocks.insert(1 if blocks and blocks[0].type == "text" else 0, Block("words", None))
        voices: dict[str, str] = {}
        for block in blocks:
            self._block(block, lesson, out, voices)

        picks = self.schedule.picks_for(lesson)
        polls = [self._manual_poll(lesson, i) for i in range(len(lesson.quiz))]
        max_polls = self.course.settings["max_polls"]
        if lesson.kind == "review":
            out.parts += self._review(picks)
            polls += self._auto_polls(lesson, picks[: self.course.settings["srs"]["review_quiz"]])
        elif lesson.kind in ("quiz", "final"):
            polls += self._auto_polls(lesson, picks)
        elif picks:
            out.parts.append(self._recall(picks, self._label("recall", lesson)))
        polls = polls[:max_polls] if lesson.kind != "final" else polls

        if polls and lesson.kind in ("quiz", "final"):
            out.parts.append(f"👇 <b>Вопросов: {len(polls)}.</b> Отвечайте по памяти и не подглядывайте, "
                             "потому что именно попытка вспомнить и закрепляет материал.")
        elif polls:
            out.parts.append(self._label("polls", lesson))
        if self.repaso_link(lesson):
            out.parts.append(self.repaso_link(lesson))

        # Уведомление приходит только о первом сообщении урока, продолжения — без звука.
        messages: list[Message] = [TextMessage(h, silent=n > 0) for n, h in enumerate(
            self._pack(self._header(lesson), out.parts, self._footer(lesson)))]
        if lesson.audio and out.audio:
            # Аудио идёт сразу после материала урока, а «Вспомним» — уже после него.
            recall = self._label("recall", lesson)
            at = next((n for n, m in enumerate(messages) if n and m.html.startswith(recall)), len(messages))
            messages.insert(at, AudioMessage(
                segments=out.audio,
                title=f"{self._label('lesson', lesson)} {lesson.number} · {self.kind_label(lesson)}",
                caption=self._label("audio", lesson),
                pauses=lesson.kind in ("vocab", "phonetics"),
            ))
        messages += [PollMessage(p.question, p.options, p.correct, p.explanation) for p in polls]
        return messages

    # ------------------------------------------------------------ части поста

    def _label(self, key: str, lesson: Lesson) -> str:
        ru, es = LABELS[key]
        return es if not self.lexicon.unknown_words(strip_tags(es), lesson) else ru

    def kind_label(self, lesson: Lesson) -> str:
        es = KIND_ES.get(lesson.kind)
        if es and not self.lexicon.unknown_words(es, lesson):
            return es
        return lesson.kind_label

    def _header(self, lesson: Lesson) -> str:
        unit = lesson.unit
        return (
            f"🇪🇸 <b>{self._label('lesson', lesson)} {lesson.number}</b> · {escape(lesson.level)} · "
            f"{self._label('unit', lesson)} {unit.number}. {to_html(unit.title)}\n"
            f"{lesson.kind_emoji} {self.kind_label(lesson)} · <b>{to_html(lesson.title)}</b>"
        )

    def repaso_link(self, lesson: Lesson) -> str:
        """Ссылка на повторение в боте: слова этого урока, а если в уроке нет новых слов — все пройденные."""
        bot = self.course.bot
        if not bot:
            return ""
        if any(item.srs for item in lesson.vocab):
            start = "l-" + re.sub(r"[^A-Za-z0-9_-]", "-", lesson.id)
            text = "Повторить слова урока"
        else:
            start, text = "repaso", "Повторить пройденные слова"
        return f'🔁 <a href="https://t.me/{bot}?start={start}">{text}</a> в боте: карточки с озвучкой.'

    def _footer(self, lesson: Lesson) -> str:
        return f"#{lesson.level} #{lesson.kind_tag}"

    def _pack(self, header: str, parts: list[str], footer: str) -> list[str]:
        # Telegram открывает все спойлеры сообщения одним нажатием, поэтому каждая
        # рубрика со скрытым текстом («Проверьте себя», «Вспомним», перевод диалога…)
        # уходит своим сообщением: ответы одной не открываются вместе с другой.
        messages, current, hidden = [], header, False
        for part in [p for p in parts if p] + [footer]:
            candidate = f"{current}\n\n{part}"
            has_spoiler = "<tg-spoiler>" in part
            if (visible_len(candidate) > TEXT_LIMIT or hidden and has_spoiler) and current:
                messages.append(current)
                current, hidden = part, has_spoiler
            else:
                current, hidden = candidate, hidden or has_spoiler
        messages.append(current)
        return messages

    def _voice(self, speaker: str, lesson_voices: dict[str, str], explicit: dict) -> str:
        if speaker not in lesson_voices:
            gender = explicit.get(speaker) or self.course.gender_of(speaker)
            if gender not in ("f", "m"):
                gender = "f" if sum(v.startswith("f") for v in lesson_voices.values()) <= \
                    sum(v.startswith("m") for v in lesson_voices.values()) else "m"
            n = sum(v.startswith(gender) for v in lesson_voices.values()) + 1
            lesson_voices[speaker] = f"{gender}{min(n, 3)}"
        return lesson_voices[speaker]

    # ------------------------------------------------------------ блоки

    def _block(self, block: Block, lesson: Lesson, out: _Out, voices: dict[str, str]) -> None:
        t, d = block.type, block.data
        narrator = "f1"
        if t == "text":
            out.parts.append(to_html(d))
        elif t == "header":
            out.parts.append(f"<b>{to_html(d)}</b>")
        elif t == "rule":
            out.parts.append(f"<blockquote>📌 {to_html(d)}</blockquote>")
        elif t in ("tip", "note", "culture"):
            icon = {"tip": "💡", "note": "📝", "culture": "🌍"}[t]
            out.parts.append(f"{icon} {to_html(d)}")
        elif t == "latam":
            out.parts.append(f"🌎 <b>В Латинской Америке:</b> {to_html(d)}")
        elif t == "task":
            out.parts.append(f"{self._label('task', lesson)} {to_html(d)}")
        elif t in ("cando", "list"):
            lines = [f"• {to_html(s)}" for s in d]
            if t == "cando":
                lines.insert(0, "✅ <b>Теперь вы умеете:</b>")
            out.parts.append("\n".join(lines))
        elif t == "words":
            out.parts.append(self._words(lesson.vocab, out, self._label("new_words", lesson)))
        elif t == "examples":
            lines = [f"<b>{to_html(d['title'])}</b>"] if d.get("title") else []
            for ex in d["items"]:
                es, ru = to_html(ex.es), to_html(ex.ru)
                if d.get("hide") == "ru":
                    lines.append(f"▫️ <i>{es}</i> — <tg-spoiler>{ru}</tg-spoiler>")
                elif d.get("hide") == "es":
                    lines.append(f"▫️ {ru} — <tg-spoiler>{es}</tg-spoiler>")
                else:
                    lines.append(f"▫️ <i>{es}</i> — {ru}")
                out.audio.append((narrator, plain(ex.es)))
            out.parts.append("\n".join(lines))
        elif t == "table":
            lines = [f"<b>{to_html(d['title'])}</b>"] if d.get("title") else []
            for row in d["rows"]:
                lines.append(" — ".join(to_html(c) for c in row))
            out.parts.append("\n".join(lines))
        elif t == "conjugation":
            out.parts.append(self._conjugation(d, out))
        elif t == "exercise":
            title = d.get("title") or strip_tags(self._label("exercise", lesson))
            lines = [f"✍️ <b>{to_html(title)}</b>"]
            for n, (q, a) in enumerate(d["items"], 1):
                line = f"{n}. {to_html(q)}"
                if a:
                    line += f" → <tg-spoiler>{to_html(a)}</tg-spoiler>"
                lines.append(line)
            out.parts.append("\n".join(lines))
        elif t == "dialogue":
            lines = [f"💬 <b>{to_html(d['title'])}</b>"] if d.get("title") else []
            if d.get("hidden"):
                lines.append(self._label("hidden_text", lesson))
            for speaker, es, ru in d["lines"]:
                text = f"<tg-spoiler>{to_html(es)}</tg-spoiler>" if d.get("hidden") else to_html(es)
                line = f"— <b>{escape(speaker)}:</b> {text}"
                if ru:
                    line += f"\n<tg-spoiler>{to_html(ru)}</tg-spoiler>"
                lines.append(line)
                out.audio.append((self._voice(speaker, voices, d["voices"]), plain(es)))
            out.parts.append("\n".join(lines))
        elif t == "reading":
            title = f"📖 <b>{to_html(d['title'])}</b>\n" if d.get("title") else ""
            text = f"{title}{to_html(d['text'])}"
            if d["translation"]:
                text += (f"\n\n<blockquote expandable>{self._label('translation', lesson)}\n"
                         f"<tg-spoiler>{to_html(d['translation'])}</tg-spoiler></blockquote>")
            out.parts.append(text)
            out.audio.append((narrator, plain(d["text"])))
        else:  # pragma: no cover
            raise ValueError(t)

    def _words(self, vocab: list[VocabItem], out: _Out, label: str) -> str:
        lines = [label]
        for item in vocab:
            icon = f"{item.emoji} " if item.emoji else "▫️ "
            line = f"{icon}<b>{escape(item.es)}</b>"
            if item.pron:
                line += f" [{escape(item.pron)}]"
            line += f" — {to_html(item.ru)}"
            if item.example:
                line += f"\n      <i>{to_html(item.example.es)}</i> — {to_html(item.example.ru)}"
            if item.note:
                line += f"\n      💡 {to_html(item.note)}"
            lines.append(line)
            out.audio.append(("f1", item.speech))
            if item.example:
                out.audio.append(("f1", plain(item.example.es)))
        return "\n".join(lines)

    def _conjugation(self, d: dict, out: _Out) -> str:
        verb = d["verb"]
        title = d.get("title") or f"{verb}" + (f" — {d['ru']}" if d.get("ru") else "")
        _, _, stem, reflexive = morph.split_verb(verb)
        lines = [f"<b>{to_html(title)}</b>"]
        for n, (person, form) in enumerate(zip(morph.PERSONS, d["forms"])):
            shown = escape(form)
            if d.get("highlight", True):
                if stem and form.startswith(stem) and len(form) > len(stem):
                    shown = f"{escape(form[:len(stem)])}<b>{escape(form[len(stem):])}</b>"
                else:
                    shown = f"<b>{escape(form)}</b>"
            pronoun = f" {REFLEXIVE_BY_PERSON[n]}" if reflexive else ""
            lines.append(f"{escape(person)}{pronoun} {shown}")
            out.audio.append(("f1", f"{person.split('/')[0]}{pronoun} {form}"))
        return "\n".join(lines)

    def _recall(self, picks: list[Pick], label: str) -> str:
        lines = [label]
        for pick in picks:
            lines.append(self._recall_line(pick))
        return "\n".join(lines)

    @staticmethod
    def _recall_line(pick: Pick) -> str:
        es, ru = escape(pick.item.es), to_html(pick.item.ru)
        if pick.production:
            return f"▫️ {ru} — <tg-spoiler>{es}</tg-spoiler>"
        return f"▫️ <i>{es}</i> — <tg-spoiler>{ru}</tg-spoiler>"

    def _review(self, picks: list[Pick]) -> list[str]:
        if not picks:
            return []
        recognise = [p for p in picks if not p.production]
        produce = [p for p in picks if p.production]
        parts = []
        if recognise:
            parts.append("\n".join(["<b>1. Узнайте слово</b> и переведите его на русский:"]
                                   + [self._recall_line(p) for p in recognise]))
        if produce:
            parts.append("\n".join([f"<b>{2 if recognise else 1}. Вспомните по-испански:</b>"]
                                   + [self._recall_line(p) for p in produce]))
        examples = [p.item.example for p in picks if p.item.example][:6]
        if examples:
            parts.append("\n".join(["<b>Слова в контексте:</b> прочитайте примеры вслух и переведите их."]
                                   + [f"▫️ <i>{to_html(e.es)}</i> — <tg-spoiler>{to_html(e.ru)}</tg-spoiler>"
                                      for e in examples]))
        return parts

    def _known_items(self, lesson: Lesson) -> list[VocabItem]:
        return [it for it in self.lexicon.items if it.lesson.index <= lesson.index]

    def _auto_polls(self, lesson: Lesson, picks: list[Pick]) -> list[Poll]:
        known = self._known_items(lesson)
        polls = []
        for pick in picks:
            poll = vocab_poll(pick, known, seed=f"{lesson.id}:{pick.item.es}")
            if poll:
                polls.append(poll)
        return polls

    def _manual_poll(self, lesson: Lesson, i: int) -> Poll:
        q = lesson.quiz[i]
        options = [plain(o) for o in q.options]
        order = list(range(len(options)))
        if q.shuffle:
            random.Random(f"{lesson.id}:quiz:{i}").shuffle(order)
        explanation = to_html(q.explain) if q.explain else ""
        return Poll(
            question=plain(q.question),
            options=[options[j] for j in order],
            correct=order.index(q.correct),
            explanation=explanation,
        )


def poll_problems(poll: PollMessage) -> list[str]:
    """Проверка ограничений Telegram для опросов."""
    problems = []
    if not 1 <= len(poll.question) <= 300:
        problems.append(f"вопрос длиннее 300 символов: {poll.question[:40]}…")
    if not 2 <= len(poll.options) <= 10:
        problems.append(f"вариантов должно быть 2–10: {poll.question[:40]}…")
    for option in poll.options:
        if not 1 <= len(option) <= 100:
            problems.append(f"вариант длиннее 100 символов: {option[:40]}…")
    if len(set(poll.options)) != len(poll.options):
        problems.append(f"повторяются варианты: {poll.question[:40]}…")
    if poll.explanation:
        visible = plain(poll.explanation)
        if visible_len(poll.explanation) > MAX_EXPLANATION or visible.count("\n") > 2:
            problems.append(f"пояснение длиннее 200 символов или 2 строк: {visible[:40]}…")
    return problems
