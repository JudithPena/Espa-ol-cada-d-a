"""Командная строка: python -m espanol <команда>.

    validate            проверить курс (словарь, лимиты Telegram, разметку)
    stats               статистика по темам и словам
    preview N|id        показать урок так, как он уйдёт в Telegram
    export [-o file]    HTML-превью всего курса для вычитки
    lookup слово        в каком уроке слово (форма) впервые появляется
    status              прогресс публикации
    check               проверить токен бота и доступ к каналу
    publish             опубликовать следующий урок (для cron / GitHub Actions)
    send N|id           отправить конкретный урок (например, себе для проверки)
                        --rich — постом-статьёй, --chat auto — в личку тому, кто последним написал боту
    run --at 09:00      постоянный режим с расписанием
"""

from __future__ import annotations

import argparse
import logging
import sys

from .config import load_settings
from .course import load_course
from .lexicon import Lexicon
from .markup import check_html, visible_len
from .publisher import Publisher, describe
from .render import PollMessage, Renderer, TextMessage, poll_problems
from .srs import Schedule


def build(settings):
    course = load_course(settings.content_dir)
    lexicon = Lexicon(course)
    renderer = Renderer(course, lexicon, Schedule(course, lexicon))
    return course, lexicon, renderer


def make_publisher(settings, course, renderer, need_api: bool = True) -> Publisher:
    api = None
    if need_api:
        from .telegram import TelegramAPI

        api = TelegramAPI(settings.token)
    return Publisher(
        course, renderer, api, settings.chat_id, settings.state_file, tz=settings.timezone,
        posts_per_day=settings.posts_per_day, audio=settings.audio, tts_rate=settings.tts_rate,
        voices=settings.voices, delay=settings.delay,
    )


def validate(course, lexicon, renderer) -> list[str]:
    problems = [str(issue) for issue in lexicon.check()]
    for lesson in course.lessons:
        for message in renderer.render(lesson):
            where = f"Урок {lesson.number} ({lesson.id})"
            if isinstance(message, TextMessage):
                if visible_len(message.html) > 4096:
                    problems.append(f"{where}: сообщение длиннее 4096 символов")
                problems += [f"{where}: {p}" for p in check_html(message.html)]
            elif isinstance(message, PollMessage):
                problems += [f"{where}: {p}" for p in poll_problems(message)]
    return problems


def cmd_validate(args, settings) -> int:
    course, lexicon, renderer = build(settings)
    problems = validate(course, lexicon, renderer)
    for p in problems:
        print("❌", p)
    words = len(course.items)
    print(f"\nУроков: {len(course.lessons)}, тем: {len(course.units)}, слов и выражений: {words}")
    print("✅ Ошибок нет" if not problems else f"Найдено проблем: {len(problems)}")
    return 1 if problems else 0


def cmd_stats(args, settings) -> int:
    course, lexicon, _ = build(settings)
    total = 0
    print(f"{'№':>3}  {'тема':<38} {'ур.':>4} {'слов':>5} {'всего':>6}")
    for unit in course.units:
        words = sum(len(lesson.vocab) for lesson in unit.lessons)
        total += words
        print(f"{unit.number:>3}  {unit.title[:38]:<38} {len(unit.lessons):>4} {words:>5} {total:>6}")
    kinds: dict[str, int] = {}
    for lesson in course.lessons:
        kinds[lesson.kind_label] = kinds.get(lesson.kind_label, 0) + 1
    print("\nТипы постов: " + ", ".join(f"{k} — {v}" for k, v in kinds.items()))
    print(f"Словоформ, известных к концу курса: {len(lexicon.known_at[-1])}")
    return 0


def render_lesson(renderer, lesson, rich: bool):
    if rich:
        from .rich import RichRenderer

        return RichRenderer(renderer).render(lesson)
    return renderer.render(lesson)


def cmd_preview(args, settings) -> int:
    course, _, renderer = build(settings)
    lesson = course.lesson(args.ref)
    for i, message in enumerate(render_lesson(renderer, lesson, args.rich), 1):
        body = message.html if args.html and hasattr(message, "html") else describe(message)
        print(f"\n——— сообщение {i} ———\n{body}")
    return 0


def cmd_export(args, settings) -> int:
    from .export import export_html

    course, _, renderer = build(settings)
    path = export_html(course, renderer, args.out, fragment=args.fragment)
    print(f"Превью сохранено: {path}")
    return 0


def cmd_lookup(args, settings) -> int:
    course, lexicon, _ = build(settings)
    for word in args.words:
        lesson = lexicon.first_seen.get(word.lower())
        if lesson:
            print(f"«{word}»: впервые в уроке {lesson.number} ({lesson.id}) — {lesson.title}")
        else:
            print(f"«{word}»: в курсе не вводится")
    return 0


def cmd_status(args, settings) -> int:
    course, _, renderer = build(settings)
    publisher = make_publisher(settings, course, renderer, need_api=False)
    state = publisher.state()
    lesson, sent = publisher.next_lesson(state)
    done = len(state.published_ids() & {lesson.id for lesson in course.lessons})
    print(f"Опубликовано: {done} из {len(course.lessons)}")
    if state.published:
        print(f"Последний: {state.published[-1]['id']} ({state.published[-1]['at']})")
    if lesson:
        extra = f", продолжить с сообщения {sent + 1}" if sent else ""
        print(f"Следующий: урок {lesson.number} — {lesson.kind_label} · {lesson.title}{extra}")
    else:
        print("Курс опубликован полностью 🎓")
    return 0


def cmd_check(args, settings) -> int:
    from .telegram import TelegramAPI

    api = TelegramAPI(settings.token)
    me = api.get_me()
    print(f"Бот: @{me.get('username')} ({me.get('first_name')})")
    if not settings.chat_id:
        print("❌ TELEGRAM_CHAT_ID не задан")
        return 1
    chat = api.call("getChat", {"chat_id": settings.chat_id})
    print(f"Чат: {chat.get('title') or chat.get('username')} (id {chat.get('id')}, {chat.get('type')})")
    member = api.call("getChatMember", {"chat_id": settings.chat_id, "user_id": me["id"]})
    status = member.get("status")
    can_post = status == "creator" or member.get("can_post_messages", status == "administrator")
    print(f"Статус бота в чате: {status}" + ("" if can_post else " — ❌ нет права публиковать"))
    return 0 if can_post or chat.get("type") != "channel" else 1


def cmd_publish(args, settings) -> int:
    course, _, renderer = build(settings)
    publisher = make_publisher(settings, course, renderer, need_api=not args.dry_run)
    if not args.dry_run and not settings.chat_id:
        print("❌ Не задан TELEGRAM_CHAT_ID", file=sys.stderr)
        return 1
    print(publisher.publish_next(force=args.force, dry_run=args.dry_run))
    return 0


def cmd_send(args, settings) -> int:
    course, _, renderer = build(settings)
    publisher = make_publisher(settings, course, renderer)
    chat = args.chat or settings.chat_id
    where = chat
    if chat == "auto":  # id не попадает в публичный лог GitHub Actions
        found = publisher.api.latest_private_chat()
        if not found:
            print("Не нашёл личного чата: напишите боту любое сообщение (например, /start) и повторите.")
            return 1
        chat, where = str(found["id"]), "личный чат того, кто последним написал боту"
    lesson = course.lesson(args.ref)
    publisher.send(render_lesson(renderer, lesson, args.rich), chat, lesson=lesson)
    print(f"Отправлен урок {lesson.number} ({lesson.id}) в {where}")
    return 0


def cmd_run(args, settings) -> int:
    from .scheduler import parse_times, run_forever

    course, _, renderer = build(settings)
    publisher = make_publisher(settings, course, renderer)
    times = parse_times(args.at or ["09:00"])
    run_forever(publisher.publish_next, times, settings.timezone)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m espanol", description="Español cada día — бот курса испанского")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="проверить курс")
    sub.add_parser("stats", help="статистика курса")
    p = sub.add_parser("preview", help="показать урок")
    p.add_argument("ref", help="номер урока (вводный — 0) или id")
    p.add_argument("--html", action="store_true", help="показать HTML вместо текста")
    p.add_argument("--rich", action="store_true", help="в виде поста-статьи (Rich Messages)")
    p = sub.add_parser("export", help="HTML-превью курса")
    p.add_argument("-o", "--out", default="preview/index.html")
    p.add_argument("--fragment", action="store_true", help="без <html>/<head>, только содержимое страницы")
    p = sub.add_parser("lookup", help="где впервые встречается слово")
    p.add_argument("words", nargs="+")
    sub.add_parser("status", help="прогресс публикации")
    sub.add_parser("check", help="проверить бота и канал")
    p = sub.add_parser("publish", help="опубликовать следующий урок")
    p.add_argument("--dry-run", action="store_true", help="только показать, ничего не отправлять")
    p.add_argument("--force", action="store_true", help="игнорировать лимит постов в день")
    p = sub.add_parser("send", help="отправить урок в указанный чат")
    p.add_argument("ref")
    p.add_argument("--chat", help="chat_id (по умолчанию TELEGRAM_CHAT_ID); auto — личный чат, "
                                  "из которого боту последним написали")
    p.add_argument("--rich", action="store_true", help="отправить постом-статьёй (Rich Messages)")
    p = sub.add_parser("run", help="постоянный режим")
    p.add_argument("--at", action="append", help="время публикации ЧЧ:ММ (можно несколько)")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    settings = load_settings()
    handler = globals()[f"cmd_{args.command}"]
    return handler(args, settings)


if __name__ == "__main__":
    sys.exit(main())
