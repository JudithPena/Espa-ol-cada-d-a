"""Сайт курса в духе Busuu: уроки по порядку, упражнения, прогресс и повторение слов.

    python -m espanol site                    # site/index.html — открыть в браузере
    python -m espanol site --units 0-5        # только темы 0–5
    python -m espanol site --fragment         # без <html>/<head> (для встраивания)

Сайт — одна страница без сервера (шаблон espanol/site_template.html). Сюда выгружаются
уроки курса как данные: слова с карточками-разборами из content/repaso/, блоки урока в HTML,
упражнения «вопрос => ответ» и тесты. Шаги урока, варианты ответов и повторение по интервалам
собирает уже страница, а прогресс ученика хранится в его браузере (localStorage).
"""

from __future__ import annotations

import base64
import json
import re
import shutil
from pathlib import Path

from .course import FEATURES, GRADED_BLOCKS, RULE_TARGETS, SOURCE_BLOCKS, Block, Course, Lesson, QuizItem, VocabItem
from .lexicon import _FUNCTION_WORDS, generated_forms
from .markup import checkable, plain, to_html
from .site_audio import cast
from .tokens import spanish_words
from .wordcards import WordCard
from .grammar import load_grammar, write_theory_illustrations

TEMPLATE = Path(__file__).with_name("site_template.html")

# Вводный урок рассказывает о канале: как выходят посты, где комментировать. На сайте он не нужен.
SKIP_KINDS = {"intro"}

# Фразы для упражнения «Соберите фразу»: столько слов, не больше и не меньше.
BUILD_MIN, BUILD_MAX = 3, 8


def _html(text: str | None) -> str:
    """Мини-разметка → HTML страницы: спойлеры Telegram становятся кнопками-подсказками."""
    if not text:
        return ""
    html = to_html(str(text)).replace("\n", "<br>")
    return html.replace("<tg-spoiler>", '<span class="spoiler" tabindex="0">').replace("</tg-spoiler>", "</span>")


# Бот на Cloudflare: вход через Telegram и хранение прогресса учеников сайта (bot/src/site.js).
SITE_API = "https://espanol-cada-dia-bot.zhurnal.workers.dev"
ART = Path(__file__).resolve().parent.parent / "content" / "art"
ART_SLUGS = {
    "la casa": "casa", "el café": "cafe", "el taxi": "taxi", "el hotel": "hotel", "la música": "musica",
    "el jamón": "jamon", "el queso": "queso", "la guitarra": "guitarra", "la paella": "paella",
    "la tortilla": "tortilla", "España": "espana", "la cerveza": "cerveza", "la plaza": "plaza",
    "el chocolate": "chocolate", "el perro": "perro", "el vino": "vino",
    "¡Hola!": "hola", "gracias": "gracias", "sí": "si", "no": "no", "el señor": "senor", "la señora": "senora",
    "por favor": "por_favor", "perdón": "perdon", "bien": "bien", "muy bien": "muy_bien", "regular": "regular",
    "mal": "mal", "buenos días": "buenos_dias", "buenas tardes": "buenas_tardes", "buenas noches": "buenas_noches",
    "adiós": "adios",
    # лист 5 ноября: «ты», «вы» и вежливые фразы с персонажами диалогов (docs/word_art_guide.md)
    "tú": "tu", "usted": "usted", "yo": "yo", "él": "el_pron", "ella": "ella", "muchas gracias": "muchas_gracias",
    "de nada": "de_nada", "hasta luego": "hasta_luego", "hasta mañana": "hasta_manana",
    # листы 2–4 (5 ноября): знакомство и команды на уроке, вещи, профессии
    "me llamo...": "me_llamo", "¿Cómo te llamas?": "como_te_llamas", "encantado/a": "encantado", "mucho gusto": "mucho_gusto",
    "escucha": "escucha", "repite": "repite", "lee": "lee", "escribe": "escribe", "responde": "responde",
    "el libro": "libro", "el cuaderno": "cuaderno", "el bolígrafo": "boligrafo", "la mochila": "mochila", "la llave": "llave",
    "la mesa": "mesa", "la silla": "silla", "el ordenador": "ordenador", "el móvil": "movil",
    "el profesor / la profesora": "profesor", "el médico / la médica": "medico", "el/la estudiante": "estudiante",
    "el camarero / la camarera": "camarero", "el ingeniero / la ingeniera": "ingeniero",
    "el programador / la programadora": "programador", "el hospital": "hospital", "la escuela": "escuela", "la oficina": "oficina",
    # листы 5–7: ещё вещи, семья, работа и учёба
    "la puerta": "puerta", "la ventana": "ventana", "el reloj": "reloj", "la lámpara": "lampara", "el lápiz": "lapiz",
    "la botella": "botella", "las gafas": "gafas", "el dinero": "dinero", "el restaurante": "restaurante",
    "la familia": "familia", "el padre": "padre", "la madre": "madre", "el hermano / la hermana": "hermano",
    "el hijo / la hija": "hijo", "el abuelo / la abuela": "abuelo", "el marido": "marido", "el novio / la novia": "novio",
    "el gato": "gato", "trabajar": "trabajar", "estudiar": "estudiar", "la universidad": "universidad",
    "el/la periodista": "periodista", "el abogado / la abogada": "abogado", "el enfermero / la enfermera": "enfermero",
    "el cocinero / la cocinera": "cocinero", "escuchar": "escuchar", "cocinar": "cocinar",
    # листы 8–13: внешность, характер, цвета, дом, мебель и «где?», состояние
    "el chico / la chica": "chico", "alto/a": "alto", "bajo/a": "bajo", "joven": "joven", "rubio/a": "rubio",
    "moreno/a": "moreno", "guapo/a": "guapo", "delgado/a": "delgado", "mayor": "mayor", "simpático/a": "simpatico",
    "antipático/a": "antipatico", "inteligente": "inteligente", "divertido/a": "divertido", "serio/a": "serio", "tímido/a": "timido",
    "trabajador/a": "trabajador", "cansado/a": "cansado", "contento/a": "contento", "rojo/a": "rojo", "azul": "azul",
    "verde": "verde", "amarillo/a": "amarillo", "blanco/a": "blanco", "negro/a": "negro", "marrón": "marron",
    "el ojo": "ojo", "el pelo": "pelo", "el piso": "piso", "la habitación": "habitacion", "el dormitorio": "dormitorio",
    "el salón": "salon", "la cocina": "cocina", "el baño": "bano", "el balcón": "balcon", "la cama": "cama",
    "el sofá": "sofa", "el armario": "armario", "la estantería": "estanteria", "la nevera": "nevera", "la tele": "tele",
    "la ducha": "ducha", "encima de": "encima", "debajo de": "debajo", "al lado de": "al_lado", "delante de": "delante",
    "detrás de": "detras", "entre": "entre", "cerca de": "cerca", "lejos de": "lejos", "triste": "triste",
    "nervioso/a": "nervioso", "enfermo/a": "enfermo", "ocupado/a": "ocupado", "aburrido/a": "aburrido",
}


# Сложные сцены (много людей) — крупно над словом, даже если слово короткое: в 96 px их не разглядеть.
ART_BIG = {"familia"}


# Картинки к объяснениям (листы 2×2 из ChatGPT): урок → {первая ячейка строки таблицы: файл в content/art}.
# Картинка встаёт в свою строку таблицы, рядом с буквой, которую поясняет.
ROW_ART = {
    "start/consonants1": {"h": "cons-1", "ñ": "cons-2", "ll": "cons-3", "j": "cons-4"},
}


AVATARS = ART / "avatars"


def avatars() -> dict[str, str]:
    """Аватары персонажей диалогов (content/art/avatars/<slug>.webp) — один раз на страницу, диалоги ссылаются по slug."""
    if not AVATARS.is_dir():
        return {}
    return {f.stem: "data:image/webp;base64," + base64.b64encode(f.read_bytes()).decode()
            for f in sorted(AVATARS.glob("*.webp"))}


def _art_file(slug: str) -> str:
    return "data:image/webp;base64," + base64.b64encode((ART / f"{slug}.webp").read_bytes()).decode()


def art_uri(es: str) -> str | None:
    """Картинка слова из content/art (лист из нейросети, нарезанный на части) как data-URI."""
    slug = ART_SLUGS.get(es)
    path = ART / f"{slug}.webp" if slug else None
    if not path or not path.exists():
        return None
    return "data:image/webp;base64," + base64.b64encode(path.read_bytes()).decode()


# «На заметку» на сайте: только фразы без непройденных слов и без отступлений про Латинскую Америку.
_NOTE_SENTENCE = re.compile(r"(?<=[.!?…»)])\s+(?=[A-ZА-ЯЁÁÉÍÓÚÑ¡¿«*_`])")
_OFF_TOPIC = re.compile(r"Латинск|Америк|Мексик|Аргентин|🌎|🌍")


def site_note(text: str | None, unknown) -> str | None:
    """Заметка к слову для сайта: фразы с непройденными словами (unknown(text) → список) выкидываем."""
    if not text:
        return None
    keep = [s for s in _NOTE_SENTENCE.split(text.strip())
            if not _OFF_TOPIC.search(s) and not [w for w in unknown(s) if len(w) > 2]]
    if keep:  # «И v — как b» без первой фразы: союз в начале убираем
        keep[0] = re.sub(r"^(?:И|А|Но|Так же|Также)[,]?\s+(\S)", lambda m: m[1].upper() if m[1].isalpha() and not m[1].isascii() else m[1], keep[0])
    return " ".join(keep) or None


# Заметки на карточке слова (ТЗ автора 5 ноября: жёлтый блок был почти на каждой карточке и перестал замечаться).
# Видно сразу («На заметку») — только то, на чём реально ошибаются: путаница, «а не…», ложные друзья.
# Остальное (произношение, второстепенные нюансы) — свёрнуто в «Подробнее». Повтор того, что и так видно
# на карточке (род при артикле, «знак ударения: X»), не показываем.
_IMPORTANT = re.compile(r"не путайте|не путать|спутать|путают|,? а не\b|не «|≠|ложн|не значит|не переводится|"
                        r"в отличие|различа|не нужен|без артикля|похож|— одно слово|не говорят|нельзя|никогда|только с\b|только в\b|всегда с\b", re.I)
_OBVIOUS = re.compile(r"^(?:(?:el|la|los|las|un|una)\s+\S+\s+—\s+)?(?:мужского|женского) рода(?::\s*(?:el|la|los|las|un|una)\s+[^.,;]+)?\.?$"
                      r"|^Знак ударения:\s*[^.,;]+\.?$", re.I)


def note_levels(es: str, trap: str | None, pron: str | None, note: str | None) -> tuple[str | None, list[list[str]]]:
    """(видимая заметка, свёрнутые [заголовок, текст]) для карточки слова; тексты — уже отфильтрованные site_note."""
    article = re.match(r"(?:el|la|los|las|un|una)\s", es, re.I)
    if trap:
        kept = [x for x in _NOTE_SENTENCE.split(trap.strip()) if not (_OBVIOUS.match(x.strip()) and (article or x.startswith("Знак")))]
        trap = " ".join(kept).strip() or None
    main = trap if trap and _IMPORTANT.search(trap) else None
    more = []
    if trap and not main:
        more.append(["Нюанс", trap])
    if pron:
        more.append(["Произношение", pron])
    if note and note not in (trap, pron):
        more.append(["Ещё", note])
    return main, more


def _word(item: VocabItem, card: WordCard | None, unknown=lambda text: []) -> dict:
    data = {
        "es": plain(item.es), "ru": plain(item.ru), "pron": item.pron, "emoji": item.emoji,
        "pos": item.pos, "say": item.speech, "srs": item.srs,
    }
    if img := art_uri(data["es"]):
        data["img"] = img
        if ART_SLUGS.get(data["es"]) in ART_BIG:
            data["imgBig"] = True
    if note := site_note(item.note, unknown):
        data["note"] = _html(note)
    examples = card.examples if card and card.examples else (
        [(item.example.es, item.example.ru)] if item.example else [])
    if examples:
        data["ex"] = [[plain(es), plain(ru)] for es, ru in examples]
    if card:
        if card.meaning:
            data["meaning"] = _html(card.meaning)
        for key, value in (("pronNote", card.pron), ("trap", card.trap)):
            if value := site_note(value, unknown):
                data[key] = _html(value)
        if card.collocations:
            data["coll"] = [_html(c) for c in card.collocations]
    main, more = note_levels(data["es"], site_note(card.trap, unknown) if card else None,
                             site_note(card.pron, unknown) if card else None, site_note(item.note, unknown))
    if main:
        data["noteMain"] = _html(main)
    if more:
        data["noteMore"] = [[t, _html(x)] for t, x in more]
    return data


# Выбор транскрипции («Как читается queso? кэ́со | куэ́со») на сайте не задаём: произношение
# проверяем на слух. В канале эти задания остаются.
_TRANSCRIPTION = re.compile(r"\s*\[[^\]]+\]\s*(?:—\s*)?")
_LATIN_WORD = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{2,}")
_LATIN = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]")


def without_transcription(answer: str | None) -> str | None:
    """Ответ упражнения без транскрипции: «[ла пла́θа] — площадь» → «площадь».

    Если в ответе была одна транскрипция («el queso => [эль кэ́со]»), то ответа не остаётся: None.
    """
    if not answer:
        return answer
    m = _TRANSCRIPTION.match(answer)
    return answer if not m else (answer[m.end():].strip() or None)


def is_transcription_quiz(quiz: QuizItem) -> bool:
    """«Как читается «vino»?» с вариантами без латиницы: би́но | ви́но | фи́но."""
    return "читается" in quiz.question.lower() and not any(_LATIN.search(plain(o)) for o in quiz.options)


# «Где ударение?»: если в слове есть значок ударения (café, música), ответ виден и спрашивать нечего.
_SYLLABLES = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:-[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)+")
_ACCENT = re.compile(r"[áéíóú]", re.I)


def is_visible_stress_quiz(quiz: QuizItem) -> bool:
    """«Где ударение в слове «café»?» — значок ´ уже показывает ответ."""
    word = re.search(r"«([^»]+)»", quiz.question)
    return "ударени" in quiz.question.lower() and bool(word and _ACCENT.search(word.group(1)))


def stress_options(answer: str) -> list[str] | None:
    """Ответ «ho-TEL» → варианты с ударением на каждом слоге: [«HO-tel», «ho-TEL»].

    Так вопрос проверяет правило: соседние ответы («CA-sa», «TA-xi») выдали бы слово по буквам.
    """
    if not _SYLLABLES.fullmatch(answer) or answer == answer.lower():
        return None
    syllables = answer.lower().split("-")
    return ["-".join(x.upper() if k == n else x for k, x in enumerate(syllables)) for n in range(len(syllables))]


# Предложения про механику канала: на сайте нет спойлеров, опросов, комментариев и постов.
_TELEGRAM = re.compile(r"\b(?:спойлер|опрос|комментари|голосов\w* сообщ|пост\w{0,3}\b|спрятан|откройте (?:его|ответ|текст)|вместо «(?:урок|вспомним|перевод)»)", re.I)
_SENTENCE = re.compile(r"(?<=[.!?…])\s+(?=[А-ЯЁA-Z¿¡«_*])")


def without_telegram(text: str) -> str:
    """Текст блока без предложений про канал; пустая строка — блок на сайте не нужен.

    Вслед за убранным предложением уходит и «Можно начать так: …» — это образец для комментария.
    Если от разметки остался непарный ** или _, блок убираем целиком: обрывок хуже, чем ничего.
    """
    lines = []
    for line in text.split("\n"):
        kept, dropped = [], False
        for sentence in _SENTENCE.split(line):
            dropped = bool(_TELEGRAM.search(sentence)) or (dropped and sentence.startswith(("Можно начать", "Например")))
            if not dropped:
                kept.append(sentence)
        if kept or not line.strip():
            lines.append(" ".join(kept))
    out = "\n".join(lines).strip()
    if out.count("**") % 2 or out.count("_") % 2 or len(plain(out)) < 25:
        return ""
    return out


_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")


def _rule_items(text: str) -> list[dict] | None:
    """Правило «1. … 2. … 3. …» → карточки: условие и примеры отдельно (примеры — крупно, с озвучкой).

    Примеры выделяем, только если после последнего «: » идёт короткий испанский перечень без кириллицы.
    Если правило не в виде нумерованного списка, возвращаем None и показываем его как раньше.
    """
    lines = [ln for ln in text.strip().split("\n") if ln.strip()]
    if len(lines) < 2 or not all(_NUMBERED.match(ln) for ln in lines):
        return None
    items = []
    for ln in lines:
        body = _NUMBERED.match(ln).group(1)
        cards = _card(body)
        items.append(cards[0] if len(cards) == 1 else _one(body))
    return items


_CYR = re.compile("[А-Яа-яЁё]")
_EXAMPLE = re.compile(r"^(?P<es>[^\[\]]+?)(?:\s*\[(?P<pron>[^\]]+)\])?$")
_SENTENCE_END = re.compile(r"(?<=[.!?…»)])\s+(?=[A-ZА-ЯЁ¡¿«(*`])")


# Перечень курсивных фраз: «_¡Hola, buenos días!_, _¡Buenos días, María!_» или «_Lee, por favor_ («Прочитай»)».
# Запятые внутри _…_ — часть фразы, плитку делим только по границам курсива.
_ITALIC_ITEM = re.compile(r"_(?P<es>[^_]+?)_(?:\s*\(«(?P<ru>[^»]+)»\)|\s+—\s+«(?P<ru2>[^»]+)»)?")
_ITALIC_SEP = re.compile(r"^(?:[\s,;]|\b(?:и|а|но|или)\b)*$")


def _italic_examples(tail: str) -> list[list[str]] | None:
    """Хвост только из курсивных фраз (с переводом в скобках или без) → [[html, озвучка, транскрипция, перевод]]."""
    tail = tail.strip().rstrip(".;")
    out, pos = [], 0
    for m in _ITALIC_ITEM.finditer(tail):
        if not _ITALIC_SEP.match(tail[pos:m.start()]):
            return None
        es, ru = m["es"].strip(), m["ru"] or m["ru2"] or ""
        if _CYR.search(es) or len(es.split()) > 8 or "**" in es or "..." in es or "…" in es:
            return None
        parts = [x.strip() for x in es.split(",")]
        if not ru and len(parts) > 1 and not re.search(r"[¡!¿?.—]", es) and all(1 <= len(x.split()) <= 3 for x in parts):
            out += [[_html(x), plain(x), "", ""] for x in parts]   # «_el libro, el cuaderno_» — перечень, а не фраза
        else:
            out.append([_html(es), plain(es), "", ru])
        pos = m.end()
    if not out or len(out) > 10 or not _ITALIC_SEP.match(tail[pos:]):
        return None
    return out


def _examples(tail: str) -> list[list[str]] | None:
    """«casa, taxi» или «café [кафэ́], hotel [отэ́ль]» → [[html, озвучка, транскрипция]]; иначе None."""
    if tail.lstrip().startswith("_") and (ex := _italic_examples(tail)):
        return ex
    items = [w.strip(" .") for w in tail.rstrip(" .").split(",")]
    if not 1 <= len(items) <= 6:
        return None
    out = []
    for item in items:
        if item.count("**") % 2 or item.replace("**", "").count("_") % 2 or "..." in item or "…" in item:
            return None  # «_¡Hola, buenos días!_» — одна фраза с запятой внутри, а не перечень
        if ("¡" in item) != ("!" in item) or ("¿" in item) != ("?" in item):
            return None
        m = _EXAMPLE.match(item)
        if not m or _CYR.search(m["es"]) or len(m["es"].split()) > 3 or not plain(m["es"]).strip():
            return None
        out.append([_html(m["es"]), plain(m["es"]), m["pron"] or ""])
    return out


def esc_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_KEY = re.compile(r"\*\*(.+?)\*\*")
_MEANS = re.compile(r"(?P<w>\*\*[^*]+\*\*|`[^`]+`|(?<!\w)_[^_]+_(?!\w))(?P<mid>[^«»:*`_]*?)(?:означает|значит) «(?P<ru>[^»]+)»")
_PARENS = re.compile(r"\s*\(([^()]+)\)")


def _one(text: str, **extra) -> dict:
    # Цветом выделяем главную мысль — жирный русский текст, а не жирные испанские слова-примеры.
    text = text.strip()
    key = any(_CYR.search(m) for m in _KEY.findall(text))
    return {"html": _html(text), "ex": [], "key": key, **extra}


_TRAILING_ITALIC = re.compile(r"^(?P<head>.*?[.!?»)])\s+(?P<tail>(?:_[^_]+_[\s.,;]*)+)$", re.S)


def _card(text: str) -> list[dict]:
    """Одна мысль → карточки: условие текстом, испанские примеры — крупными плитками с озвучкой.

    • «**sí** со значком означает «да», а `si` без значка означает «если»» → пары «слово → значение»;
    • «… мужского рода (el café, el hotel), а … женского рода (la casa)» → по карточке на каждую скобку;
    • «…: casa, taxi» или «…: café [кафэ́], hotel [отэ́ль]» → плитки после последнего «: ».
    """
    means = list(_MEANS.finditer(text))
    if len(means) >= 2:
        head = text[:means[0].start()].rstrip(" :")
        pairs = []
        for k, m in enumerate(means):
            nxt = means[k + 1].start() if k + 1 < len(means) else m.end()
            # «…означает «до потом», то есть «до встречи», а …» — уточнение остаётся под своей парой
            note = re.sub(r"^[\s,:;]+|[\s,:;]*(?:\b(?:а|и|но)\b)?[\s,:;]*$", "", text[m.end():nxt])
            if note and not re.match(r"(?:то есть|а дословно|дословно|или)\b", note):
                if "_" in note or "." in note or len(note.split()) > 3:
                    break   # между парами целая мысль или примеры — оставляем предложение текстом
                note = ""   # связка вроде «а если сказать»: пары и так её показывают
            pairs.append([esc_html(plain(m["w"])), plain(m["w"]), _html(m["mid"].strip(" ,")), m["ru"],
                          _html(note) if note else ""])
    if len(means) >= 2 and len(pairs) == len(means):
        if len(head.split()) <= 2 and "**" not in head:
            head = ""   # «Слово», «Поэтому», «Например,» без пар ничего не значат
        card = _one(head, pairs=pairs)
        tail = text[means[-1].end():].strip()
        if tail.startswith(":") and (ex := _examples(tail[1:])):
            card["ex"] = ex
        elif tail.strip(" .,:;"):
            return [card, _one(tail.lstrip(" ,:;"))]
        return [card]
    groups = [m for m in _PARENS.finditer(text) if (ex := _examples(m[1])) and len(ex) >= 2]
    if groups:
        cards, start = [], 0
        for m in groups:
            card = _one(re.sub(r"^(а|и|но)\s+", "", text[start:m.start()].strip(" ,")))
            card["ex"] = _examples(m[1])
            cards.append(card)
            start = m.end()
        rest = text[start:].strip(" ,.")
        if rest:
            cards.append(_one(rest))
        return cards
    head, sep, tail = text.rpartition(": ")
    ex = _examples(tail) if sep and head.strip() else None
    if not ex and (m := _TRAILING_ITALIC.match(text)) and (ex := _italic_examples(m["tail"])):
        head = m["head"]   # «…говорят **hay**. _Hay un libro._ _Hay dos libros._» — примеры после точки
    card = _one(head if ex else text)
    card["ex"] = ex or []
    return [card]


def _lead(card: dict) -> bool:
    return not card["ex"] and not card.get("pairs") and not card["key"] and len(re.sub("<[^>]+>", "", card["html"])) <= 90


def _text_cards(text: str) -> list[dict]:
    """Абзац → карточки, по одной мысли (предложению) на карточку."""
    parts = [p.strip() for p in _SENTENCE_END.split(text.strip()) if p.strip()]
    if any(p.count("**") % 2 or p.count("`") % 2 or p.replace("**", "").count("_") % 2 for p in parts):
        parts = [text.strip()]
    return [c for p in parts for c in _card(p)]


def _block(block: Block) -> dict | None:
    t, d = block.type, block.data
    if t == "words":
        return None  # новые слова страница показывает карточками в начале урока
    if t == "task" and _TELEGRAM.search(d):
        return None  # «Напишите в комментариях…»: на сайте писать некуда
    if t in ("text", "tip", "note", "task"):
        text = without_telegram(d)
        if not text:
            return None
        lines = [ln for ln in text.strip().split("\n") if ln.strip()]
        if t in ("text", "note", "tip") and (items := _rule_items(text)):
            return {"t": t, "html": _html(text), "items": items}   # «1. … 2. … 3. …» — шаги, как у правила
        plain_lines = not any(re.match(r"\s*(?:[-•|]|\d+[.)])", ln) for ln in lines)
        cards = ([c for ln in lines for c in _text_cards(ln)]
                 if t in ("text", "note", "tip") and plain_lines else None)
        if cards and t == "text" and len(cards) > 1 and _lead(cards[0]):
            cards[0]["lead"] = True   # короткая первая мысль — крупной строкой, не карточкой
        return {"t": t, "html": _html(text), **({"cards": cards} if cards else {})}
    if t == "rule" and (items := _rule_items(d)):
        return {"t": t, "html": "", "items": items}
    if t in ("rule", "latam", "culture", "header"):
        return {"t": t, "html": _html(d)}
    if t == "list":
        # Пункт с эмодзи в начале — шаг шкалы (☀️ утро → 🌇 день → 🌙 вечер): значок, мысль, плитки примеров.
        steps = []
        for x in d:
            m = re.match(r"^\s*([^\w\s*_`«(\[¡¿]+)\s+(.*)$", x)
            icon, body = (m[1], m[2]) if m else ("", x)
            cards = _card(body.rstrip(";"))
            steps.append({"icon": icon, **(cards[0] if len(cards) == 1 else _one(body))})
        return {"t": t, "items": [_html(x) for x in d], "steps": steps}
    if t == "cando":
        return {"t": t, "items": [_html(x) for x in d]}
    if t == "examples":
        return {"t": t, "title": _html(d["title"]),
                "items": [[_html(ex.es), _html(ex.ru), plain(ex.es)] for ex in d["items"]]}
    if t == "table":
        return {"t": t, "title": _html(d["title"]), "rows": [[_html(c) for c in row] for row in d["rows"]]}
    if t == "conjugation":
        return {"t": t, "verb": d["verb"], "forms": d["forms"], "title": _html(d["title"]),
                "ru": _html(d["ru"])}
    if t == "dialogue":
        return {"t": t, "title": _html(d["title"]), "hidden": d["hidden"], "join": d.get("join", False),
                "cast": cast(list(dict.fromkeys(speaker for speaker, _, _ in d["lines"]))),
                "lines": [[speaker, _html(es), _html(ru), plain(es)] for speaker, es, ru in d["lines"]]}
    if t == "compare":
        return {"t": t, "style": d["style"], "join": d["join"], "title": _html(d["title"]), "lead": _html(d["lead"]), "note": _html(d["note"]),
                "cards": [{"head": _html(c["head"]), "say": plain(c["head"]) if c["say"] and _LATIN_WORD.search(c["head"]) else "",
                           "label": _html(c["label"]), "html": _html(c["text"]), "tone": c["tone"], "key": False,
                           "ex": [[_html(es), plain(es), "", ru] for es, ru in c["ex"]]} for c in d["cards"]]}
    if t == "reading":
        return {"t": t, "title": _html(d["title"]), "html": _html(d["text"]),
                "tr": _html(d["translation"]), "say": plain(d["text"])}
    if t in SCENARIO:
        return SCENARIO[t](d)
    if t == "exercise":
        items = []
        for q, raw in d["items"]:
            a = without_transcription(raw)
            if raw and not a:
                continue
            item = {"q": _html(q), "a": _html(a), "qp": plain(q), "ap": plain(a or "")}
            options = stress_options(item["ap"])
            if options:
                if _ACCENT.search(item["qp"]):
                    continue  # «el café => ca-FÉ»: значок ´ уже показывает ответ
                item["opts"] = options
            items.append(item)
        # На сайте упражнение — выбор из вариантов, поэтому «проверьте» в заголовке → «выберите».
        title = re.sub(r"\bпроверьте\b", "выберите", d["title"] or "")
        return {"t": t, "title": _html(title), "items": items} if items else None
    raise ValueError(f"блок {t} не поддерживается сайтом")  # pragma: no cover


# ---------------------------------------------------------------- сценарий урока (блоки сайта)
# Данные для страницы: варианты и ответы — в двух видах, HTML для показа и чистый текст для проверки
# и озвучки. Первый вариант выбора — верный, страница перемешивает их в каждой попытке.

def _is_es(text: str) -> bool:
    """Испанский текст (озвучиваем): есть латиница и нет кириллицы."""
    return bool(_LATIN_WORD.search(text)) and not _CYR.search(text)


def _say(text: str) -> str:
    text = plain(text)
    return text if _is_es(text) else ""


def _img(es: str) -> str:
    """Картинка задания — слово курса с картинкой (ART_SLUGS): страница берёт её из карточки слова."""
    return es if es and es in ART_SLUGS else ""


def _lines(lines) -> tuple[dict, list]:
    voices = cast(list(dict.fromkeys(sp for sp, _, _ in lines))) if lines else {}
    return voices, [[sp, _html(es), _html(ru), plain(es)] for sp, es, ru in lines]


def _task_meta(meta: dict) -> dict:
    """source / free / rule / skill задания как их написал автор; ссылки разрешает lesson_data."""
    return {k: meta[k] for k in ("source", "free", "rule", "skill") if meta.get(k)}


def _choose(d) -> dict:
    items = []
    for it in d["items"]:
        voices, lines = _lines(it["lines"])
        na = it.get("noaudio")
        items.append({"q": _html(it["q"]), "o": [[_html(o), plain(o)] for o in it["options"]],
                      "explain": _html(it["explain"]), "say": plain(it["say"]), "lines": lines, "cast": voices,
                      "img": _img(it["img"]), **_task_meta(it.get("meta") or {}),
                      # пояснение к неверному варианту: ключ — вариант как текст
                      "mistakes": {plain(k): _html(v) for k, v in (it.get("meta") or {}).get("mistakes", {}).items()},
                      **({"noaudio": {"q": _html(na["q"]), "o": [[_html(o), plain(o)] for o in na["options"]],
                                      "explain": _html(na["explain"])}} if na else {})})
    return {"t": "choose", "title": _html(d["title"]), "items": items}


_SPECIAL = re.compile("[áéíóúüñÁÉÍÓÚÜÑ]")


def _write(d) -> dict:
    # Кнопки á é í ó ú ü ñ — в блоке, где такие буквы есть хотя бы в одном ответе (во всех его заданиях,
    # чтобы кнопки не выдавали, в каком ответе они нужны). Для артиклей кнопки не нужны.
    chars = any(_SPECIAL.search(a) for it in d["items"] for a in it["answers"])
    def noaudio(na, fmt):
        return {"q": _html(na["q"]), "a": [plain(a) for a in na["answers"]], "show": _html(na["answers"][0]),
                "format": na["format"] or fmt, "explain": _html(na["explain"])}
    return {"t": "write", "title": _html(d["title"]), "accents": d["accents"], "chars": chars, "items": [{
        "q": _html(it["q"]), "a": [plain(a) for a in it["answers"]], "show": _html(it["answers"][0]),
        "explain": _html(it["explain"]), "say": plain(it["say"]), "format": it["format"] or d["format"],
        "img": _img(it["img"]), **_task_meta(it.get("meta") or {}),
        # пояснение к ожидаемой ошибке ввода: ключ — ответ ученика (страница сравнивает без регистра и ударений)
        "mistakes": {plain(k): _html(v) for k, v in (it.get("meta") or {}).get("mistakes", {}).items()},
        **({"noaudio": noaudio(it["noaudio"], it["format"] or d["format"])} if it.get("noaudio") else {}),
    } for it in d["items"]]}


SCENARIO = {
    "learn": lambda d: {"t": "learn", "words": [plain(es) for es in d]},
    "choose": _choose,
    "write": _write,
    "match": lambda d: {"t": "match", "title": _html(d["title"]),
                        "pairs": [[plain(a), plain(b), _say(a), _say(b)] for a, b in d["pairs"]]},
    "sort": lambda d: {"t": "sort", "title": _html(d["title"]),
                       "groups": [[_html(name), [[plain(x), _say(x)] for x in xs]] for name, xs in d["groups"]]},
    "build": lambda d: {"t": "build", "title": _html(d["title"]),
                        "items": [{"es": plain(it["es"]), "ru": plain(it["ru"]), "alt": [plain(a) for a in it["alt"]],
                                   "extra": [plain(x) for x in it["extra"]], **_task_meta(it.get("meta") or {})}
                                  for it in d["items"]]},
    "mission": lambda d: {"t": "mission", "title": _html(d["title"]), "html": _html(d["text"])},
    "more": lambda d: {"t": "more", "title": _html(d["title"]), "html": _html(d["text"]), "join": True},
    "recap": lambda d: {"t": "recap", "title": _html(d["title"]), "words": d["words"], "phrase": plain(d["phrase"])},
    "review": lambda d: {"t": "review", "title": _html(d["title"]), "skills": d["skills"], "n": d["n"]},
}


def _sentences(lesson: Lesson) -> list[list[str]]:
    """Фразы урока с переводом для «Соберите фразу»: примеры, диалоги, примеры к словам."""
    pairs: list[tuple[str, str]] = []
    for item in lesson.vocab:
        if item.example:
            pairs.append((item.example.es, item.example.ru))
    for block in lesson.blocks:
        if block.type == "examples":
            pairs += [(ex.es, ex.ru) for ex in block.data["items"]]
        elif block.type == "dialogue":
            pairs += [(es, ru) for _, es, ru in block.data["lines"]]
    out, seen = [], set()
    for es, ru in pairs:
        es, ru = plain(es).strip(), plain(ru).strip()
        if not ru or es in seen or not BUILD_MIN <= len(es.split()) <= BUILD_MAX:
            continue
        seen.add(es)
        out.append([es, ru])
    return out


def _split(block: Block) -> list[dict]:
    """Длинный текст делим по пустым строкам: один абзац — одна мысль, а не простыня на экран."""
    if block.type == "text":
        parts = [p for p in re.split(r"\n\s*\n", str(block.data)) if p.strip()]
        return [b for part in parts if (b := _block(Block("text", part)))]
    b = _block(block)
    return [b] if b else []


# Задания, которые без своего урока не понять: вопросы к диалогу или тексту и всё после миссии
# («Вы — Марко…»). «🔁 Вспомним» и «Фразы и конструкции» их не берут (ctx). Новый виток урока
# (порция слов, правило, таблица) снимает метку; после миссии она остаётся до конца урока.
_CONTEXT = {"dialogue", "reading", "mission"}
_NEW_CYCLE = {"learn", "rule", "compare", "table", "header", "examples", "conjugation", "list"}


def mark_context(blocks: list[dict]) -> None:
    ctx = mission = False
    for b in blocks:
        t = b["t"]
        if t == "mission":
            mission = True
        if t in _CONTEXT:
            ctx = True
        elif t in _NEW_CYCLE:
            ctx = mission
        if t in ("choose", "write") and ctx:
            b["ctx"] = True


# Виток урока для «📖 Повторить правило»: объяснение ищем назад до этих блоков (новая порция слов, источник,
# повторение) или до заголовка. Задания внутри витка пропускаем: правило может стоять двумя заданиями выше.
_CYCLE_STOP = {"learn", "dialogue", "reading", "mission", "review", "recap", "header"}


def rule_run(blocks: list[Block], k: int) -> list[int]:
    """Номера блоков ближайшего объяснения того же витка перед заданием k (без явного rule)."""
    run: list[int] = []
    for j in range(k - 1, -1, -1):
        t = blocks[j].type
        if t in GRADED_BLOCKS or t == "exercise":
            if run:
                break
            continue
        if t in _CYCLE_STOP:
            break
        if t in RULE_TARGETS:
            run.insert(0, j)
    return run


def resolve_refs(lesson: Lesson, blocks: list[dict], pieces: list[list[int]]) -> None:
    """Ссылки заданий на источник (src) и правило (rule) — номера блоков страницы; skill — теги навыков.

    pieces[k] — номера блоков страницы, на которые разошёлся блок урока k (длинный текст делится на абзацы).
    Источник у перестроенных уроков только явный: source: id или free: true (проверяет espanol/scenario.py).
    """
    ids = {b.meta["id"]: k for k, b in enumerate(lesson.blocks) if b.meta.get("id")}
    first = lambda k: pieces[k][0] if pieces[k] else None
    def rule_of(spec: str | None, k: int) -> list[int]:
        if spec == "none":
            return []
        if spec:
            j = ids.get(spec)
            if j is None:
                return []
            more = []
            for m in range(j + 1, len(lesson.blocks)):   # «Подробнее» под объяснением — вместе с ним
                if lesson.blocks[m].type != "more":
                    break
                more.append(m)
            return [x for m in [j, *more] for x in pieces[m]]
        return [x for m in rule_run(lesson.blocks, k) for x in pieces[m]]
    def apply(target: dict, own: dict, block: Block, k: int) -> None:
        source = own.get("source") or (None if own.get("free") else block.meta.get("source"))
        free = bool(own.get("free") or (not own.get("source") and block.meta.get("free")))
        for key in ("source", "free"):
            target.pop(key, None)
        if source and source in ids and lesson.blocks[ids[source]].type in SOURCE_BLOCKS:
            target["src"] = first(ids[source])
        if free:
            target["free"] = True
        target["rule"] = rule_of(own.get("rule") or block.meta.get("rule"), k)
        skill = own.get("skill") or block.meta.get("skill")
        if skill:
            target["skill"] = list(skill)
    for k, block in enumerate(lesson.blocks):
        if block.type not in GRADED_BLOCKS or not pieces[k]:
            continue
        b = blocks[pieces[k][0]]
        if block.type in ("match", "sort"):
            apply(b, {}, block, k)
        else:
            for it, raw in zip(b["items"], block.data["items"]):
                apply(it, raw.get("meta") or {}, block, k)


def lesson_data(lesson: Lesson, cards: dict[str, WordCard], lexicon=None) -> dict:
    unknown = (lambda text: lexicon.unknown_words(text, lesson)) if lexicon else (lambda text: [])
    blocks, pieces = [], []
    for block in lesson.blocks:
        out = _split(block)
        if out:
            if block.meta.get("id"):
                out[0]["id"] = block.meta["id"]
            if block.meta.get("slide"):
                out[0]["slide"] = block.meta["slide"]
            if block.meta.get("join"):
                out[0]["join"] = True
        pieces.append(list(range(len(blocks), len(blocks) + len(out))))
        blocks += out
    resolve_refs(lesson, blocks, pieces)
    if lesson.version < 2:
        mark_context(blocks)   # ещё не перестроенный урок: прежняя метка «вопрос к диалогу»
    by_cell = ROW_ART.get(lesson.id, {})
    for blk in blocks:
        if by_cell and blk["t"] == "table":
            cells = [re.sub("<[^>]*>", "", row[0]) for row in blk["rows"]]
            blk["rowpics"] = {str(k): _art_file(by_cell[c]) for k, c in enumerate(cells) if c in by_cell}
    return {
        "n": lesson.number, "id": lesson.id, "unit": lesson.unit.number, "level": lesson.level,
        "kind": lesson.kind, "kindLabel": lesson.kind_label, "emoji": lesson.kind_emoji,
        "title": plain(lesson.title), "goal": plain(lesson.goal), "scripted": lesson.scripted,
        "version": lesson.version, "check": lesson.check,
        "words": [_word(item, cards.get(item.key), unknown) for item in lesson.vocab],
        "blocks": blocks,
        "quiz": [{"q": plain(q.question), "options": [plain(o) for o in q.options], "correct": q.correct,
                  "shuffle": q.shuffle, "explain": _html(q.explain), **_quiz_refs(lesson, pieces, q)}
                 for q in lesson.quiz if not is_transcription_quiz(q) and not is_visible_stress_quiz(q)],
        "sentences": _sentences(lesson),
    }


def _quiz_refs(lesson: Lesson, pieces: list[list[int]], q: QuizItem) -> dict:
    """Вопрос теста к диалогу или тексту урока (source: id) и его навык."""
    ids = {b.meta["id"]: k for k, b in enumerate(lesson.blocks) if b.meta.get("id")}
    out: dict = {}
    k = ids.get(q.meta.get("source") or "")
    if k is not None and lesson.blocks[k].type in SOURCE_BLOCKS and pieces[k]:
        out["src"] = pieces[k][0]
    if q.meta.get("free"):
        out["free"] = True
    if q.meta.get("skill"):
        out["skill"] = list(q.meta["skill"])
    rule = q.meta.get("rule")
    if rule and rule != "none" and rule in ids:
        out["rule"] = pieces[ids[rule]]
    return out


def word_forms(course: Course) -> dict[str, str]:
    """Форма слова → слово курса (es): по нажатию на «tengo» страница покажет «tener».

    Сначала слова из одного слова (существительное без артикля, глагол, прилагательное), потом
    фразы: «buenos» из «buenos días» не перебьёт отдельное слово. Артикли и предлоги
    из чужих фраз не берём: «la» не должно открывать «la casa».
    """
    single, phrases = [], []
    for item in course.items:
        (single if all(len(core.split()) == 1 for core in item.cores) else phrases).append(item)
    verbs = {core.lower(): item for item in course.items if item.pos == "verb" for core in item.cores}
    forms: dict[str, str] = {}
    for item in single + phrases:
        own = {w.lower() for core in item.cores for w in spanish_words(core)} if item in single else set()
        found = item.base_forms() | generated_forms(item, set(FEATURES)) | {f.lower() for f in item.extra_forms}
        for form in sorted(found):
            if form in own or form not in _FUNCTION_WORDS:
                forms.setdefault(form, plain(item.es))
    for lesson in course.lessons:  # формы из таблиц спряжения
        for block in lesson.blocks:
            verb = verbs.get(block.data["verb"].lower()) if block.type == "conjugation" else None
            if verb:
                for form in block.data["forms"]:
                    for word in spanish_words(form):
                        forms.setdefault(word.lower(), plain(verb.es))
    return forms


def word_phrases(course: Course) -> list[list]:
    """Фразы курса для перевода по нажатию: [[слова фразы], слово курса].

    Страница ищет их в тексте раньше отдельных слов, поэтому «buenos días» открывается целиком,
    а не как «bueno/a» и «el día». Фразы с пропуском («¿Cómo se dice... en español?») не ищем.
    """
    out, seen = [], set()
    for item in course.items:
        for core in item.cores:
            if "  " in core.strip() or len(core.split()) < 2:
                continue
            words = [w.lower() for w in spanish_words(core)]
            if len(words) > 1 and tuple(words) not in seen:
                seen.add(tuple(words))
                out.append([words, plain(item.es)])
    return sorted(out, key=lambda p: -len(" ".join(p[0])))


def video_data(video) -> dict:
    """Разбор видео для сайта: ссылка, текст по фразам, новые слова и пояснения к каждой фразе."""
    return {
        "id": video.id, "n": video.number, "title": plain(video.title), "url": video.url,
        "segments": [{
            "es": plain(seg.es), "ru": _html(seg.ru),
            "words": [{"es": plain(w.es), "ru": plain(w.ru), "pron": w.pron, "say": w.speech} for w in seg.words],
            "notes": [_html(n) for n in seg.notes],
        } for seg in video.segments],
    }



BOOK_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


def load_books(directory: Path | None = None) -> list[dict]:
    """Одна папка на книгу, отдельные файлы глав; черновики не попадают на сайт."""
    directory = Path(directory) if directory is not None else Path(__file__).resolve().parent.parent / "content" / "books"
    books, ids = [], set()
    for path in sorted(directory.glob("*/book.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        book_id = meta.get("id")
        if not isinstance(book_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", book_id) or book_id in ids:
            raise ValueError(f"{path}: некорректный или повторный id книги")
        ids.add(book_id)
        if meta.get("level") not in BOOK_LEVELS or meta.get("vocabulary_min_level") not in BOOK_LEVELS:
            raise ValueError(f"{path}: укажите уровень книги и отдельный порог лексики")
        if not all(isinstance(meta.get(k), str) and meta[k].strip() for k in ("title", "author")):
            raise ValueError(f"{path}: укажите название и автора")
        cover = meta.get("cover")
        if cover and not isinstance(cover, str):
            raise ValueError(f"{path}: обложка должна быть ссылкой или именем файла")
        if cover and not re.match(r"^https?://", cover, re.I):
            image = (path.parent / cover).resolve()
            types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
            if not image.is_relative_to(path.parent.resolve()) or image.suffix.lower() not in types or not image.is_file():
                raise ValueError(f"{path}: неверный путь к обложке")
            cover = f"data:{types[image.suffix.lower()]};base64," + base64.b64encode(image.read_bytes()).decode("ascii")
        chapters, chapter_ids, orders, numbers = [], set(), set(), set()
        for chapter_path in sorted((path.parent / "chapters").glob("*.json")):
            chapter = json.loads(chapter_path.read_text(encoding="utf-8"))
            chapter_id, number, order = chapter.get("id"), chapter.get("number"), chapter.get("order")
            if not isinstance(chapter_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", chapter_id) or chapter_id in chapter_ids:
                raise ValueError(f"{chapter_path}: некорректный или повторный id главы")
            if type(number) is not int or number < 1 or type(order) is not int or order < 1 or number in numbers or order in orders:
                raise ValueError(f"{chapter_path}: некорректный или повторный номер или порядок главы")
            title = chapter.get("title")
            if chapter.get("status") not in ("draft", "published") or (title is not None and not isinstance(title, str)):
                raise ValueError(f"{chapter_path}: неверный статус или название главы")
            title = (title or "").strip()
            if re.fullmatch(r"(?:sin t[ií]tulo|sin nombre|untitled|no title|без названия|без заголовка|нет названия|n/a|none|null|[-—])\.?", title, re.I):
                title = ""
            chapter["title"] = title
            icon = chapter.get("icon", "📖")
            if not isinstance(icon, str) or not icon.strip() or len(icon) > 16:
                raise ValueError(f"{chapter_path}: иконка главы должна быть коротким символом")
            chapter["icon"] = icon.strip()
            chapter_ids.add(chapter_id); numbers.add(number); orders.add(order)
            if chapter["status"] == "published":
                if not isinstance(chapter.get("blocks"), list) or not chapter["blocks"]:
                    raise ValueError(f"{chapter_path}: опубликованная глава пуста")
                exercise_ids = set()
                exercises = chapter.get("exercises", [])
                if not isinstance(exercises, list):
                    raise ValueError(f"{chapter_path}: задания должны быть списком")
                for exercise in exercises:
                    if not isinstance(exercise, dict):
                        raise ValueError(f"{chapter_path}: неверный формат задания")
                    ex_id = exercise.get("id")
                    if (not isinstance(ex_id, str) or not ex_id or ex_id in exercise_ids
                            or not isinstance(exercise.get("instruction"), str) or not exercise["instruction"].strip()):
                        raise ValueError(f"{chapter_path}: неверный id или инструкция задания")
                    exercise_ids.add(ex_id)
                    if not isinstance(exercise.get("questions"), list) or not exercise["questions"]:
                        raise ValueError(f"{chapter_path}: в задании нет вопросов")
                    for question in exercise["questions"]:
                        if not isinstance(question, dict):
                            raise ValueError(f"{chapter_path}: неверный формат вопроса")
                        if question.get("kind") == "reflection":
                            if not isinstance(question.get("prompt"), str) or not question["prompt"].strip():
                                raise ValueError(f"{chapter_path}: неверный вопрос для размышления")
                            continue
                        options, answer = question.get("options"), question.get("answer")
                        answers = answer if isinstance(answer, list) else [answer]
                        if (not isinstance(question.get("prompt"), str) or not question["prompt"].strip()
                                or not isinstance(options, list) or len(options) < 2
                                or not all(isinstance(v, str) and v.strip() for v in options)
                                or not answers or not all(type(a) is int and 0 <= a < len(options) for a in answers)):
                            raise ValueError(f"{chapter_path}: неверный вопрос или ответ")
                chapters.append(chapter)
        books.append({**meta, "cover": cover, "chapters": sorted(chapters, key=lambda c: c["order"])})
    return books


def site_data(course: Course, cards: dict[str, WordCard], units: set[int] | None = None,
              videos: list | None = None, preview: bool = False) -> dict:
    """preview — тестовая версия сайта: в шапке метка «тест»."""
    from .lexicon import Lexicon

    lexicon = Lexicon(course)
    lessons, carried = [], []
    for lesson in course.lessons:
        if units is not None and lesson.unit.number not in units:
            continue
        data = lesson_data(lesson, cards, lexicon)
        if lesson.kind in SKIP_KINDS:  # слова вводного урока переходят в следующий урок сайта
            carried += data["words"]
            continue
        data["words"] = carried + data["words"]
        carried = []
        lessons.append(data)
    return {
        "title": course.title,
        "preview": preview,
        "openUnits": course.settings.get("site_open_units"),
        "api": SITE_API,
        "bot": course.bot,
        "intervals": course.settings["srs"]["intervals"],
        "units": [{"number": u.number, "title": plain(u.title), "level": u.level, "goals": [plain(g) for g in u.goals]}
                  for u in course.units if units is None or u.number in units],
        "lessons": lessons,
        "videos": [video_data(v) for v in videos or []],
        "books": load_books(),
        "grammar": load_grammar(),
        "forms": word_forms(course),
        "phrases": word_phrases(course),
        "avatars": avatars(),
        # Навыки-конструкции (content/site/skills.yaml): повторение по интервалам и сильные/слабые темы итогов.
        "skills": {tag: {"title": plain(sk["title"]), "lesson": sk["lesson"]} for tag, sk in course.skills.items()},
    }


def parse_units(spec: str | None) -> set[int] | None:
    """«0-5» или «0,2,4» → номера тем; пусто — весь курс."""
    if not spec:
        return None
    numbers: set[int] = set()
    for part in spec.split(","):
        start, _, end = part.strip().partition("-")
        numbers.update(range(int(start), int(end or start) + 1))
    return numbers


ICON_DIR = Path(__file__).resolve().parent.parent / "content" / "icons"
ICON_FILES = ["apple-touch-icon.png", "favicon-32.png", "icon-192.png", "icon-512.png", "icon-maskable-512.png"]
MANIFEST = json.dumps({
    "name": "Español cada día", "short_name": "Español", "lang": "ru", "start_url": "./", "scope": "./",
    "display": "standalone", "background_color": "#2346c4", "theme_color": "#2346c4",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}, ensure_ascii=False, indent=2)


def build_site(course: Course, cards: dict[str, WordCard], out: str | Path, units: set[int] | None = None,
               fragment: bool = False, videos: list | None = None, preview: bool = False,
               audio_cache: str | Path | None = None) -> Path:
    """audio_cache — папка с записями озвучки (espanol/site_audio.py): недостающее записывается, нужное
    копируется в a/ рядом со страницей. Без неё сайт собирается без записей (так в тестах)."""
    site = site_data(course, cards, units, videos, preview)
    out = Path(out)
    if not fragment:
        write_theory_illustrations(site["grammar"], out.parent)
    if audio_cache and not fragment:
        from .site_audio import record
        site["audio"] = record(site, out.parent, audio_cache)
    data = json.dumps(site, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/{}", data)
    page = page.replace("/*__GRAMMAR_PLAYER__*/", TEMPLATE.with_name("grammar_player.js").read_text(encoding="utf-8"))
    if not fragment:
        # <title>, <meta> и <style> из шаблона браузер сам отнесёт в <head>.
        page = ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">\n'
                '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n'
                '<link rel="manifest" href="manifest.webmanifest">\n'
                '<meta name="theme-color" content="#2346c4">\n'
                '<meta name="apple-mobile-web-app-capable" content="yes">\n'
                '<meta name="mobile-web-app-capable" content="yes">\n'
                '<meta name="apple-mobile-web-app-title" content="Español">\n'
                f"{page}\n</html>\n")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    if not fragment:  # иконки и манифест лежат рядом со страницей
        for f in ICON_FILES:
            shutil.copyfile(ICON_DIR / f, out.parent / f)
        (out.parent / "manifest.webmanifest").write_text(MANIFEST, encoding="utf-8")
    return out
