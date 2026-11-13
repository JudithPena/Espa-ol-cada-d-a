#!/usr/bin/env python3
"""Обновляет progreso.md — журнал работы над курсом A2 на сайте.

    python tools/progreso.py                      — пересчитать таблицу тем и счётчики по курсу
    python tools/progreso.py "Тема 29 «…» (8 уроков)."   — и дописать строку в журнал с сегодняшней датой

Таблица тем и строка «Сейчас» собираются из content/site (число уроков и слов — фактические); строки журнала
и остальные разделы файла сохраняются как есть.
"""
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from espanol.course import load_course  # noqa: E402

# Программа A2 (docs/a2_c2_curriculum_map.md): номер темы, название, что в ней.
PLAN = [
    (24, "El español y yo", "desde / desde hace / hace… que; para / porque; saber / conocer; me cuesta; анкета и алфавит"),
    (25, "¿Qué hiciste ayer?", "pretérito indefinido: правильные глаголы, ir / ser, hacer, estar, tener; выходные"),
    (26, "Una vida", "биография; годы и сотни; a los 20 años; hace dos años; pude, quise, vine, dije"),
    (27, "Hoy y ayer", "perfecto и indefinido; ya, todavía no; неправильные причастия; опыт и подробности"),
    (28, "De viaje", "вокзал, аэропорт, гостиница; lo, la, los, las; ir / irse; предлоги пути"),
    (29, "En el mercado + КТ-1", "количества и меры; algo / nada, alguno / ninguno; ¿Me pone…?; контрольная точка 1"),
    (30, "Cuando era pequeño", "pretérito imperfecto: формы, привычки; antes / ahora; ya no, todavía"),
    (31, "Cómo era", "imperfecto в описании; más / menos… que, tan… como, mejor / peor"),
    (32, "¿Qué pasó?", "indefinido и imperfecto вместе; cuando, de repente, entonces, al final; estaba + герундий"),
    (33, "¿Quedamos?", "предложить, согласиться, отказаться: ¿Te apetece…?, ¿Por qué no…?, es que…"),
    (34, "Te lo recomiendo", "императив (tú, usted); le / les, se lo; рецепты и советы"),
    (35, "Por la ciudad + КТ-2", "дорога, разрешение и просьба: ¿Puedo…?, ¿Te importa…?; se безличное; контрольная точка 2"),
    (36, "Me encuentro mal", "симптомы и советы: me gustaría, podrías, deberías; врач и аптека"),
    (37, "De compras", "el más…, -ísimo; este / ese без существительного; el mío / la mía; обмен покупки"),
    (38, "Mi trabajo, mis estudios", "empezar a, dejar de, volver a, seguir + герундий; desde… hasta, durante; резюме"),
    (39, "La gente", "ser / estar с прилагательными; parecerse, llevarse bien; me parece; характер и чувства"),
    (40, "Planes y deseos", "pensar + инфинитив, me gustaría; si + настоящее; планы и праздники"),
    (41, "El mundo hispano", "повторение времён; se dice, se come; Испания и Америка"),
    (42, "Итог A2", "рассказ о поездке 100–120 слов и итог уровня (check: control)"),
]

path = ROOT / "progreso.md"
text = path.read_text(encoding="utf-8")
course = load_course(ROOT / "content" / "site")
stats = {u.number: (len(u.lessons), sum(len(lesson.vocab) for lesson in u.lessons)) for u in course.units if u.level == "A2"}
done = len(stats)
nxt = max(stats) + 1 if stats else PLAN[0][0]
titles = {n: t for n, t, _ in PLAN}

rows = []
for n, title, what in PLAN:
    if n in stats:
        rows.append(f"| {n} | {title} | {what} | {stats[n][0]} | {stats[n][1]} | ✅ готово |")
    else:
        rows.append(f"| {n} | {title} | {what} | — | — | {'⏭ следующая' if n == nxt else '⬜ не начата'} |")
table = "| № | Тема | Что в ней | Уроков | Слов | Статус |\n|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n"
now = (f"- Готово тем: **{done} из {len(PLAN)}**. Уроков A2: **{sum(v[0] for v in stats.values())}**, "
       f"новых слов и выражений: **{sum(v[1] for v in stats.values())}**.\n"
       + (f"- В работе: тема {nxt} — {titles[nxt]}{'' if titles[nxt][-1:] in '?!.' else '.'}\n" if nxt in titles else "- Все темы уровня готовы.\n"))


def section(name: str, body: str, src: str) -> str:
    """Заменяет тело раздела «## name» до следующего заголовка (или до пояснения после таблицы)."""
    pattern = re.compile(rf"(## {re.escape(name)}\n\n)(.*?)(?=\n(?:## |«Готово»))", re.S)
    if not pattern.search(src):
        sys.exit(f"в progreso.md нет раздела «{name}»")
    return pattern.sub(lambda m: m.group(1) + body, src, count=1)


text = section("Сейчас", now, text)
text = section("Темы", table, text)
if len(sys.argv) > 1:
    entry = f"| {datetime.date.today():%d.%m.%Y} | {' '.join(sys.argv[1:])} |\n"
    m = re.search(r"(## Журнал\n\n\| Дата \| Что сделано \|\n\|---\|---\|\n(?:\|.*\n)*)", text)
    if not m:
        sys.exit("в progreso.md нет таблицы журнала")
    text = text[:m.end()] + entry + text[m.end():]
path.write_text(text, encoding="utf-8")
print(f"progreso.md: готово тем {done} из {len(PLAN)}")
