"""Мини-разметка контента → HTML для Telegram.

Поддерживается:
    **жирный**   _курсив_   ||спойлер||   ~~зачёркнутый~~   `код`   https://ссылка

Текст внутри `код` не форматируется и не проверяется валидатором словаря:
так помечаются буквы, слоги, окончания и прочий «метаязык».
Ссылки становятся кликабельными и тоже не проверяются.
"""

from __future__ import annotations

import html
import re

_CODE = re.compile(r"`([^`\n]+)`")
_URL = re.compile(r"https?://[^\s<>]+[^\s<>.,;:!?)»]")
_SPOILER = re.compile(r"\|\|(.+?)\|\|", re.S)
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
# Одиночное подчёркивание — курсив; «___» (пропуск в упражнении) не трогаем.
_ITALIC = re.compile(r"(?<![\w*_])_(?![\s_])(.+?)(?<![\s_])_(?![\w_])", re.S)
_STRIKE = re.compile(r"~~(.+?)~~", re.S)
_TAG = re.compile(r"<[^>]+>")
_PLACEHOLDER = "\ue000{}\ue001"
_PLACEHOLDER_RE = re.compile("\ue000(\\d+)\ue001")

TELEGRAM_TAGS = {"b", "i", "u", "s", "tg-spoiler", "code", "pre", "blockquote", "a"}


def escape(text: str) -> str:
    return html.escape(text, quote=False)


def to_html(text: str) -> str:
    """Преобразует мини-разметку в HTML, экранируя всё остальное."""
    codes: list[str] = []

    def stash(m: re.Match) -> str:
        codes.append("<code>" + escape(m.group(1)) + "</code>")
        return _PLACEHOLDER.format(len(codes) - 1)

    def stash_url(m: re.Match) -> str:
        url = html.escape(m.group(0))
        codes.append(f'<a href="{url}">{url}</a>')
        return _PLACEHOLDER.format(len(codes) - 1)

    text = _CODE.sub(stash, text)
    text = _URL.sub(stash_url, text)
    text = escape(text)
    text = _SPOILER.sub(r"<tg-spoiler>\1</tg-spoiler>", text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _ITALIC.sub(r"<i>\1</i>", text)
    text = _STRIKE.sub(r"<s>\1</s>", text)
    return _PLACEHOLDER_RE.sub(lambda m: codes[int(m.group(1))], text)


def plain(text: str) -> str:
    """Текст без разметки (для опросов Telegram, где форматирование недоступно)."""
    text = _CODE.sub(r"\1", text)
    for rx in (_SPOILER, _BOLD, _ITALIC, _STRIKE):
        text = rx.sub(r"\1", text)
    return text


def checkable(text: str) -> str:
    """Текст для проверки словаря: без разметки, ссылок и фрагментов в `коде`."""
    text = _CODE.sub(" ", text)
    text = _URL.sub(" ", text)
    for rx in (_SPOILER, _BOLD, _ITALIC, _STRIKE):
        text = rx.sub(r"\1", text)
    return text


def strip_tags(html_text: str) -> str:
    return html.unescape(_TAG.sub("", html_text))


def tg_len(text: str) -> int:
    """Длина в единицах UTF-16 — так Telegram считает лимиты."""
    return len(text.encode("utf-16-le")) // 2


def visible_len(html_text: str) -> int:
    return tg_len(strip_tags(html_text))


def check_html(html_text: str) -> list[str]:
    """Проверяет, что теги корректно вложены и поддерживаются Telegram."""
    problems, stack = [], []
    for m in re.finditer(r"<(/?)([a-z-]+)[^>]*>", html_text):
        closing, tag = m.group(1) == "/", m.group(2)
        if tag not in TELEGRAM_TAGS:
            problems.append(f"неподдерживаемый тег <{tag}>")
        elif not closing:
            stack.append(tag)
        elif not stack or stack[-1] != tag:
            problems.append(f"неверная вложенность </{tag}>")
            break
        else:
            stack.pop()
    if stack:
        problems.append("незакрытые теги: " + ", ".join(stack))
    if re.search(r"\*\*|\|\||(?<![\w_])_(?![_\s])|~~", strip_tags(html_text)):
        problems.append("осталась необработанная разметка (** || _ ~~)")
    return problems
