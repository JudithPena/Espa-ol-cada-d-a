"""HTML-превью всего курса: посты как в ленте канала, со спойлерами и викторинами.

    python -m espanol export                 # preview/index.html — открыть в браузере
    python -m espanol export --fragment      # без <html>/<head> (для встраивания)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .course import Course
from .render import AudioMessage, PollMessage, Renderer, TextMessage

TEMPLATE = Path(__file__).with_name("preview_template.html")


def _web_html(html: str) -> str:
    """Теги Telegram → обычный HTML."""
    html = html.replace("<tg-spoiler>", '<span class="spoiler" tabindex="0">').replace("</tg-spoiler>", "</span>")
    html = html.replace("<blockquote expandable>", '<blockquote class="expandable">')
    return re.sub(r"\n(#[^\n<]+)$", r'\n<span class="tags">\1</span>', html.rstrip())


def course_data(course: Course, renderer: Renderer) -> dict:
    posts = []
    for lesson in course.lessons:
        messages = []
        for message in renderer.render(lesson):
            if isinstance(message, TextMessage):
                messages.append({"type": "text", "html": _web_html(message.html)})
            elif isinstance(message, AudioMessage):
                messages.append({
                    "type": "audio", "title": message.title, "caption": message.caption,
                    "count": len(message.segments),
                    "text": " · ".join(text for _, text in message.segments[:6]),
                })
            elif isinstance(message, PollMessage):
                messages.append({
                    "type": "poll", "q": message.question, "options": message.options,
                    "correct": message.correct, "explain": message.explanation,
                })
        posts.append({
            "n": lesson.number, "id": lesson.id, "unit": lesson.unit.number,
            "level": lesson.level, "kind": lesson.kind, "kindLabel": lesson.kind_label,
            "emoji": lesson.kind_emoji, "title": lesson.title, "words": len(lesson.vocab),
            "messages": messages,
        })
    units = [{
        "number": unit.number, "title": unit.title, "level": unit.level,
        "goals": unit.goals, "count": len(unit.lessons),
    } for unit in course.units]
    return {
        "title": course.title, "units": units, "posts": posts,
        "words": len(course.items),
    }


def export_html(course: Course, renderer: Renderer, out: str | Path, fragment: bool = False) -> Path:
    data = json.dumps(course_data(course, renderer), ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/{}", data)
    if not fragment:
        page = ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                f"</head>\n<body>\n{page}\n</body>\n</html>\n")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out
