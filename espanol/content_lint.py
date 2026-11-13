"""Проверки содержания заданий сайта (аудит MYTHOS, этап 4: TST-01…06, SYS-03, SYS-04, SYS-10).

`validate` и тесты ловят форму урока; эти проверки ловят классы ошибок в смысле заданий, найденные при
прохождении курса. Однозначное — ошибка (`errors`): цитата `evidence` не найдена в источнике. Остальное —
предупреждения (`warnings`): у прежних уроков они записаны в `content/site/lint_baseline.json` и снимаются по
мере правок; новое предупреждение в уроке — повод его исправить (тест `test_no_new_content_warnings`).

Ключ предупреждения — «урок|код|деталь»: по нему сверяется список известных.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from . import morphology as morph
from .course import Course, Lesson
from .lexicon import Issue, Lexicon
from .markup import plain
from .tokens import spanish_words

BASELINE = Path(__file__).resolve().parent.parent / "content" / "site" / "lint_baseline.json"
MAX_NEW_WORDS = 8          # новых слов в уроке сайта (правило 7 «Правил содержания заданий»)
SITE_LEVELS = ("A0", "A1", "A2", "B1", "B2", "C1")


def _norm(text: str) -> str:
    """Для сравнения цитаты с источником: без регистра, ударений, знаков и лишних пробелов."""
    t = unicodedata.normalize("NFD", plain(str(text)).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^\w\s]", " ", t).split())


def _source_text(lesson: Lesson, source: str) -> str | None:
    """Звучащий или видимый испанский текст источника: реплики без подписей, текст чтения, текст миссии."""
    for block in lesson.blocks:
        if block.meta.get("id") != source:
            continue
        d = block.data if isinstance(block.data, dict) else {}
        if block.type == "dialogue":
            return " ".join(es for _, es, _ in d.get("lines", []))
        return str(d.get("text") or "")
    return None


def _questions(lesson: Lesson):
    """Вопросы урока: (где, тип блока, вопрос, варианты, верный, пояснение, meta, блок-meta)."""
    for k, block in enumerate(lesson.blocks):
        if block.type == "choose":
            for n, it in enumerate(block.data["items"], 1):
                yield (f"choose {k + 1}.{n}", "choose", it["q"] or (it["lines"][-1][1] if it["lines"] else it.get("say", "")),
                       it["options"], 0, it["explain"], it.get("meta") or {}, block.meta)
    for n, q in enumerate(lesson.quiz, 1):
        yield (f"quiz {n}", "quiz", q.question, q.options, q.correct, q.explain, q.meta, {})


def evidence_issues(lesson: Lesson) -> list[str]:
    """TST-01: цитата evidence у вопроса к источнику есть в его репликах или тексте (подписи говорящих не считаются)."""
    out = []
    for where, _, q, _, _, _, meta, bmeta in _questions(lesson):
        ev = meta.get("evidence")
        if not ev:
            continue
        source = meta.get("source") or (bmeta.get("source") if not meta.get("free") else None)
        text = _source_text(lesson, source) if source else None
        if text is None:
            out.append(f"{where}: evidence без источника (source)")
            continue
        for quote in ev:
            if _norm(quote) not in _norm(text):
                out.append(f"{where}: цитаты «{plain(quote)[:50]}» нет в источнике «{source}» — ответ должен следовать из реплик или текста")
    return out


# ------------------------------------------------------------------ предупреждения

def _verb_forms(lexicon: Lexicon) -> dict[str, set[tuple[str, str]]]:
    """Форма → {(инфинитив, время)} для всех глаголов курса: по ним видно, что неверный вариант — настоящая форма."""
    out: dict[str, set[tuple[str, str]]] = {}
    for item in lexicon.items:
        if item.pos != "verb":
            continue
        for inf in item.cores:
            if " " in inf or not morph.is_verb(inf):
                continue
            info = morph.verb_info(inf)
            tenses = {
                "present": morph.present(inf, info),
                "preterite_irregular" if morph.is_preterite_irregular(inf) else "preterite": morph.preterite(inf, info),
                "imperfect": morph.imperfect(inf),
                "conditional": morph.conditional(inf),
                "imperative": morph.imperative(inf, info),
            }
            for tense, forms in tenses.items():
                for f in forms:
                    out.setdefault(f.lower(), set()).add((inf, tense))
    return out


_TENSE_RU = {"preterite": "pretérito indefinido", "preterite_irregular": "pretérito indefinido", "imperfect": "imperfecto",
             "conditional": "condicional", "imperative": "imperativo", "present": "настоящее время"}


def _tense_issues(lesson: Lesson, lexicon: Lexicon, forms: dict) -> list[tuple[str, str]]:
    """TST-04: неверный вариант — настоящая форма того же глагола во времени, которого ученик ещё не проходил:
    он запомнит её как ошибку (`comimos` в «Nosotros ___ en un restaurante»)."""
    nonverb = {c.lower() for item in lexicon.items if item.pos != "verb" for c in item.cores}
    out = []
    for where, _, _, options, correct, _, _, _ in _questions(lesson):
        right = [w.lower() for w in spanish_words(options[correct])]
        for k, opt in enumerate(options):
            wrong = [w.lower() for w in spanish_words(opt)]
            if k == correct or len(wrong) != len(right):
                continue
            diff = [(a, b) for a, b in zip(right, wrong) if a != b]
            if len(diff) != 1:
                continue
            a, b = diff[0]
            if a in nonverb:      # «la casa» — существительное, а не форма casarse
                continue
            lemmas = {inf for inf, _ in forms.get(a, ())}
            # Форма, которую ученик уже знает (настоящее время, пройденное прошедшее, слово урока), — честный
            # неверный вариант; незнакомая настоящая форма того же глагола — нет.
            if lexicon.is_known(b, lesson):
                continue
            for inf, tense in sorted(forms.get(b, ())):
                if inf in lemmas and tense != "present":
                    out.append((f"tense|{b}", f"{where}: неверный вариант «{b}» — настоящая форма {inf} ({_TENSE_RU[tense]}), "
                                              f"ученик её ещё не проходил и запомнит как ошибку"))
                    break
    return out


# Согласные испанского слова → какие буквы русской транскрипции им соответствуют (по порядку).
_CONS = [("ll", "льй"), ("rr", "р"), ("ch", "ч"), ("qu", "к"), ("gu", "г"), ("cc", "кс"), ("ñ", "нь"), ("b", "б"), ("v", "б"),
         ("d", "д"), ("f", "ф"), ("j", "х"), ("k", "к"), ("l", "л"), ("m", "м"), ("n", "н"), ("p", "п"), ("r", "р"),
         ("s", "с"), ("t", "т"), ("x", "кс"), ("z", "с"), ("w", "у")]


def _consonants(word: str) -> list[str]:
    """Ожидаемые русские согласные слова (h немая, y/i — гласные, c и g — по следующей букве)."""
    w = unicodedata.normalize("NFC", word.lower())
    out, i = [], 0
    while i < len(w):
        ch, nxt = w[i], w[i + 1:i + 2]
        if w.startswith(("ch", "ll", "rr", "cc"), i):
            out.append(dict(_CONS)[w[i:i + 2]]); i += 2; continue
        if ch == "c":
            out.append("с" if nxt in "eéií" and nxt else "к"); i += 1; continue
        if ch == "g":
            out.append("х" if nxt and nxt in "eéií" else "г"); i += 1; continue
        if ch in "aeiouáéíóúüyh":
            i += 1; continue
        for sp, ru in _CONS:
            if w.startswith(sp, i):
                if sp in ("qu", "gu") and w[i + 2:i + 3] not in "eéií":
                    out.append(ru); i += 1; break   # gua, guo: u читается — «гуа»
                out.append(ru); i += len(sp); break
        else:
            i += 1
    return out


def _pron_issue(es: str, pron: str) -> str | None:
    """TST-06: в транскрипции нет согласной, которая есть в слове (`[бальо́н]` у balcón)."""
    if not pron or "," in pron or "/" in pron or "…" in pron:
        return None
    words = [w for w in re.findall(r"[^\W\d_]+", es) if w.lower() not in ("el", "la", "los", "las", "un", "una")]
    if "/" in es:
        return None
    tr = re.sub(r"[^а-яёθ]", "", pron.lower().replace("ё", "е")).replace("θ", "с")   # θ — c, z в транскрипции Испании
    want = [c for w in words for c in _consonants(w)]
    pos = 0
    # Ассимиляция и особые слова: n перед b/v/p звучит [м] (invierno — [имбьэ́рно]), s перед звонкой — [з] (desde), x в México — [х].
    alt = {"н": ["н", "м"], "с": ["с", "з"], "кс": ["кс", "х", "с"]}
    for c in want:
        options = alt.get(c) or ([c] if len(c) == 1 or c == "нь" else list(c))
        found = -1
        for o in options:
            k = tr.find(o[0] if c == "нь" or o == "кс" else o, pos)
            if k >= 0 and (found < 0 or k < found):
                found = k
        if found < 0:
            return c
        pos = found + 1
    return None


_SUBJECT_START = {"el", "la", "los", "las", "mi", "mis", "tu", "tus", "su", "sus", "nuestro", "nuestra", "nuestros", "nuestras",
                  "vuestro", "vuestra", "vuestros", "vuestras", "este", "esta", "estos", "estas"}


def warnings(course: Course, lexicon: Lexicon | None = None) -> list[tuple[str, Issue]]:
    """Предупреждения о содержании заданий: (ключ, Issue)."""
    lexicon = lexicon or Lexicon(course)
    forms = _verb_forms(lexicon)
    out: list[tuple[str, Issue]] = []
    for lesson in course.lessons:
        if lesson.unit.level not in SITE_LEVELS or not lesson.scripted:
            continue
        add = lambda key, msg: out.append((f"{lesson.id}|{key}", Issue(lesson, msg)))
        # TST-05, SYS-10: размер урока
        if len(lesson.vocab) > MAX_NEW_WORDS:
            add("words", f"{len(lesson.vocab)} новых слов (не больше {MAX_NEW_WORDS}): разделите порции между уроками")
        shown = [b for b in lesson.blocks if not b.meta.get("bank")]   # банк повторения в уроке не показывается
        writes = [(b, it) for b in lesson.blocks if b.type == "write" for it in b.data["items"]]
        ear = any(it.get("say") for b in shown if b.type in ("choose", "write") for it in b.data["items"])
        produce = any(b.type in ("write", "build", "compose", "chat") for b in shown)
        # SYS-04: урок со словами без пункта на слух
        if any(b.type == "learn" for b in lesson.blocks) and not ear and lesson.kind not in ("quiz", "final", "review"):
            add("ear", "урок со словами без задания на слух (say): добавьте хотя бы два")
        # SYS-03: тест темы без воспроизведения
        if lesson.kind in ("quiz",) and not produce:
            add("produce", "в тесте темы нет ввода или сборки: добавьте 2–3 пункта по целям темы")
        # TST-02: фраза из 3+ слов с единственным допустимым ответом
        for b, it in writes:
            first, q = (it["answers"][0] if it["answers"] else ""), plain(it["q"])
            quote = re.match(r"Как .*сказано", q) or not re.search(r"[А-Яа-яЁё]", q)   # цитата из текста, исправление ошибки
            # Подлежащее названо существительным или именем (Mi padre es serio, Carlos es camarero): другого
            # естественного порядка у такой фразы нет — один ответ здесь не упущение.
            words = spanish_words(first)
            named = bool(words) and (words[0].lower() in _SUBJECT_START or (words[0][:1].isupper() and words[0] in course.names))
            if len(words) >= 3 and len(it["answers"]) == 1 and not it.get("say") and not it.get("answer") and not quote and not named:
                add(f"single|{plain(it['q'])[:40]}", f"ввод «{plain(it['q'])[:40]}»: у фразы один допустимый ответ — "
                                                     "проверьте местоимение, порядок слов, краткий ответ (шаблон ответа)")
        for key, msg in _tense_issues(lesson, lexicon, forms):
            add(key, msg)
        for item in lesson.vocab:
            miss = _pron_issue(item.es, item.pron)
            if miss:
                add(f"pron|{item.es}", f"транскрипция [{item.pron}] у «{item.es}»: нет согласной «{miss}»")
    return out


def baseline() -> set[str]:
    try:
        return set(json.loads(BASELINE.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return set()


def write_baseline(keys: list[str]) -> None:
    BASELINE.write_text("[\n" + ",\n".join(json.dumps(k, ensure_ascii=False) for k in sorted(set(keys))) + "\n]\n", encoding="utf-8")


__all__ = ["evidence_issues", "warnings", "baseline", "write_baseline", "BASELINE"]
