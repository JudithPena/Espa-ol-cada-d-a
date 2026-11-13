"""Проверки сценариев уроков сайта (content/site): порции слов, порядок и задания.

Сценарий — это список блоков урока (docs/site_lessons_guide.md). Lexicon проверяет, что в уроке только
пройденные слова, но считает все слова урока известными сразу. В сценарии слова идут порциями (`learn`),
поэтому здесь отдельно проверяем, что ни одно задание не спрашивает слово урока раньше его карточки.
"""

from __future__ import annotations

import re

from .course import FEATURES, GRADED_BLOCKS, OPEN_BLOCKS, RULE_TARGETS, SITE_ONLY_BLOCKS, SOURCE_BLOCKS, Course, Lesson
from .lexicon import SCENARIO_TEXTS, Issue, Lexicon, generated_forms, lesson_texts
from .markup import checkable, plain
from .tokens import spanish_words

MAX_OPTIONS = 5
MAX_PAIRS = 6


def _key(text: str) -> str:
    """Сравнение вариантов: без регистра, разметки и знаков."""
    return re.sub(r"[\s¿¡?!.,;:«»\"'…—–-]+", " ", plain(text).lower()).strip()


def _exact(text: str) -> str:
    """Вариант выбора как его видит ученик: без лишних пробелов, но с регистром (ho-TEL / HO-tel) и знаками ¿ ? ¡ !."""
    return " ".join(plain(text).split())


def _tile(token: str) -> str:
    """Плитка «Соберите фразу» без регистра и знаков по краям: так её сравнивает страница."""
    return re.sub(r"^[¿¡\"«]+|[.,;:!?\"»…]+$", "", token.lower())


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in spanish_words(checkable(text))]


def _graded_texts(block) -> list[str]:
    """Испанские тексты задания, по которым видно, какое слово оно проверяет (с неверными вариантами)."""
    d = block.data
    if block.type == "exercise":
        return [t for q, a in d["items"] for t in (q, a or "")]
    texts = SCENARIO_TEXTS[block.type](d)
    if block.type == "choose":
        texts += [o for it in d["items"] for o in it["options"]]
    if block.type == "build":
        texts += [x for it in d["items"] for x in it["extra"]]
    if block.type == "chat":
        texts += [o for it in d["items"] if it["kind"] == "choose" for o in it["options"]]
        texts += [x for it in d["items"] if it["kind"] == "build" for x in it["extra"]]
    return texts


def _block_issues(lesson: Lesson, block) -> list[str]:
    d, t = block.data, block.type
    out = []
    if t == "choose":
        for it in d["items"]:
            keys = [_exact(o) for o in it["options"]]
            if not 2 <= len(keys) <= MAX_OPTIONS:
                out.append(f"choose: нужно от 2 до {MAX_OPTIONS} вариантов — {it['q'] or it['say']!r}")
            if len(set(keys)) != len(keys):
                out.append(f"choose: одинаковые варианты — {it['options']!r}")
            if not (it["q"] or it["say"] or it["lines"] or it["img"]):
                out.append("choose: у вопроса нет ни q, ни say, ни lines, ни img")
    elif t == "write":
        for it in d["items"]:
            if not it["answers"]:
                out.append(f"write: нет ответа — {it['q']!r}")
            if not (it["q"] or it["say"] or it["img"]):
                out.append("write: у задания нет ни q, ни say, ни img")
    elif t == "match":
        lefts, rights = [_key(a) for a, _ in d["pairs"]], [_key(b) for _, b in d["pairs"]]
        if not 2 <= len(lefts) <= MAX_PAIRS:
            out.append(f"match: нужно от 2 до {MAX_PAIRS} пар")
        if len(set(lefts)) != len(lefts) or len(set(rights)) != len(rights):
            out.append("match: стороны пар повторяются — пару нельзя будет выбрать однозначно")
    elif t == "sort":
        items = [_key(x) for _, xs in d["groups"] for x in xs]
        if len(d["groups"]) < 2 or any(not xs for _, xs in d["groups"]):
            out.append("sort: нужно не меньше двух непустых групп")
        if len(set(items)) != len(items):
            out.append("sort: карточка повторяется — у неё будет две верные группы")
    elif t == "build":
        for it in d["items"]:
            words = it["es"].split()
            if not 2 <= len(words) <= 10:
                out.append(f"build: во фразе нужно от 2 до 10 слов — {it['es']!r}")
            for alt in it["alt"]:
                if sorted(map(_tile, alt.split())) != sorted(map(_tile, words)):
                    out.append(f"build: другой порядок должен состоять из тех же плиток — {alt!r}")
            if {_tile(x) for x in it["extra"]} & {_tile(x) for x in words}:
                out.append(f"build: лишняя плитка совпадает со словом фразы — {it['extra']!r}")
    elif t == "compose":
        for it in d["items"]:
            out += _compose_issues(it, "compose")
    elif t == "chat":
        for n, it in enumerate(d["items"], 1):
            where = f"chat, ход {n}"
            if it["kind"] == "choose":
                keys = [_exact(o) for o in it["options"]]
                if not 2 <= len(keys) <= MAX_OPTIONS or len(set(keys)) != len(keys):
                    out.append(f"{where}: нужно от 2 до {MAX_OPTIONS} разных вариантов")
            elif it["kind"] == "build":
                words = it["es"].split()
                if not 2 <= len(words) <= 10:
                    out.append(f"{where}: во фразе нужно от 2 до 10 слов — {it['es']!r}")
                for alt in it["alt"]:
                    if sorted(map(_tile, alt.split())) != sorted(map(_tile, words)):
                        out.append(f"{where}: другой порядок должен состоять из тех же плиток — {alt!r}")
                if {_tile(x) for x in it["extra"]} & {_tile(x) for x in words}:
                    out.append(f"{where}: лишняя плитка совпадает со словом фразы — {it['extra']!r}")
            elif it["kind"] == "compose":
                out += _compose_issues(it, where)
            if it["kind"] != "build" and not it["task"]:
                out.append(f"{where}: нужно условие по-русски (task): что ученик должен сказать")
    elif t == "learn":
        pass
    return out


def _flat(text: str) -> str:
    """Как страница сравнивает письмо с признаками: без регистра, знаков и ударений (ñ остаётся)."""
    text = re.sub(r"[¿¡?!.,;:«»\"“”'…()\[\]—–-]", " ", plain(text).lower())
    return " " + " ".join(text.translate(str.maketrans("áéíóú", "aeiou")).split()) + " "


def compose_passes(it: dict, text: str) -> list[bool]:
    """Какие условия письма выполняет текст (как на странице): длина, предложения, признаки."""
    flat = _flat(text)
    has = lambda p: _flat(p) in flat
    out = []
    n = len(flat.split())
    if it["words"]:
        out.append(it["words"][0] <= n <= it["words"][1])
    if it["sentences"]:
        out.append(len([x for x in re.split(r"[.!?…]+", plain(text)) if x.strip()]) >= it["sentences"])
    for c in it["checks"]:
        if c["if"] and not any(has(p) for p in c["if"]):
            out.append(True)
            continue
        ok = True
        if c["any"]:
            ok = ok and any(has(p) for p in c["any"])
        if c["all"]:
            ok = ok and all(has(p) for p in c["all"])
        if c["starts"]:
            ok = ok and any(flat.startswith(_flat(p).rstrip() + " ") for p in c["starts"])
        if c["re"]:
            ok = ok and bool(re.search(c["re"], flat.strip()))
        out.append(ok)
    return out


def _compose_issues(it: dict, where: str) -> list[str]:
    out = []
    if not (it["checks"] or it["words"] or it["sentences"]):
        out.append(f"{where}: у письма нет ни одного условия (checks, words, sentences) — проверять нечего")
    if not all(compose_passes(it, it["sample"])):
        out.append(f"{where}: образец не выполняет собственные условия — «{plain(it['sample'])[:50]}»")
    return out


def _img_issues(block) -> list[str]:
    from .site import ART, ART_SLUGS

    if block.type not in ("choose", "write"):
        return []
    bad = [it["img"] for it in block.data["items"] if it["img"] and not (it["img"] in ART_SLUGS and (ART / f"{ART_SLUGS[it['img']]}.webp").exists())]
    return [f"{block.type}: у слова «{x}» нет картинки (ART_SLUGS в espanol/site.py)" for x in bad]


def _tasks(lesson: Lesson):
    """Задания урока для проверки ссылок: (номер блока, блок, поля вопроса или None для пар и групп, где)."""
    for k, block in enumerate(lesson.blocks):
        if block.type in ("choose", "write", "build", "compose", "chat"):
            for n, it in enumerate(block.data["items"], 1):
                yield k, block, it.get("meta") or {}, f"{block.type}, вопрос {n}"
        elif block.type in ("match", "sort"):
            yield k, block, {}, block.type


def _ref_issues(lesson: Lesson, skills: dict, index: dict[str, int]) -> list[str]:
    """Ссылки сценария: id блоков, источник (source), правило (rule), навыки (skill) и запланированное повторение."""
    out: list[str] = []
    ids: dict[str, int] = {}
    for k, block in enumerate(lesson.blocks):
        bid = block.meta.get("id")
        if bid:
            if bid in ids:
                out.append(f"id «{bid}» стоит у двух блоков")
            ids[bid] = k
            if block.type not in SOURCE_BLOCKS | RULE_TARGETS | {"chat"}:   # у разговора id — имя его ленты
                out.append(f"id «{bid}» у блока {block.type}: id ставят источникам и объяснениям")
    def skill_issues(tags, where, k=None):
        for tag in tags or []:
            sk = skills.get(tag)
            if not sk:
                out.append(f"{where}: навыка «{tag}» нет в content/site/skills.yaml")
            elif sk["lesson"] not in index:
                out.append(f"skills.yaml: у навыка «{tag}» нет урока {sk['lesson']}")
            elif index[sk["lesson"]] > lesson.index:
                out.append(f"{where}: навык «{tag}» вводится позже, в уроке {sk['lesson']}")
    def ref_issues(meta, where, k):
        src, rule = meta.get("source"), meta.get("rule")
        if src:
            j = ids.get(src)
            if j is None:
                out.append(f"{where}: source «{src}» — в уроке нет блока с таким id")
            elif lesson.blocks[j].type not in SOURCE_BLOCKS:
                out.append(f"{where}: source «{src}» — это {lesson.blocks[j].type}, а источник — диалог, текст или миссия")
            elif k is not None and j > k:
                out.append(f"{where}: source «{src}» стоит после задания")
        if rule and rule != "none":
            j = ids.get(rule)
            if j is None:
                out.append(f"{where}: rule «{rule}» — в уроке нет блока с таким id")
            elif lesson.blocks[j].type not in RULE_TARGETS:
                out.append(f"{where}: rule «{rule}» — это {lesson.blocks[j].type}, а правило — объяснение")
            elif k is not None and j > k:
                out.append(f"{where}: rule «{rule}» стоит после задания")
        skill_issues(meta.get("skill"), where)
    for k, block, meta, where in _tasks(lesson):
        ref_issues(block.meta, f"{block.type}", k)
        ref_issues(meta, where, k)
        if block.type in ("choose", "write"):
            for n, it in enumerate(block.data["items"], 1):
                if it.get("noaudio") and not it["say"]:
                    out.append(f"{block.type}, вопрос {n}: noaudio бывает только у задания на слух (say)")
                if block.type == "choose":
                    wrong = {_exact(o) for o in it["options"][1:]}
                    for key in (it.get("meta") or {}).get("mistakes", {}):
                        if _exact(key) not in wrong:
                            out.append(f"choose, вопрос {n}: mistakes «{key}» — нет такого неверного варианта")
    for n, q in enumerate(lesson.quiz, 1):
        ref_issues(q.meta, f"тест, вопрос {n}", None)
    for k, block in enumerate(lesson.blocks):
        if block.type == "review":
            for tag in block.data["skills"]:
                sk = skills.get(tag)
                if not sk:
                    out.append(f"review: навыка «{tag}» нет в content/site/skills.yaml")
                elif index.get(sk["lesson"], 10**6) >= lesson.index:
                    out.append(f"review: навык «{tag}» вводится не раньше этого урока — повторять пока нечего")
    return out


def _strict_issues(lesson: Lesson) -> list[str]:
    """Перестроенный урок (version ≥ 2): у каждого задания после источника явная привязка — source или free;
    каждое слово урока проверяется заданием или стоит в recap."""
    out: list[str] = []
    seen_source = False
    for k, block in enumerate(lesson.blocks):
        if block.type in SOURCE_BLOCKS:
            seen_source = True
            continue
        if not seen_source or block.type not in GRADED_BLOCKS:
            continue
        bound = block.meta.get("source") or block.meta.get("free")
        if block.type == "chat":   # разговор сам себе источник: его ходы идут подряд и вне разговора не задаются
            continue
        if block.type in ("match", "sort"):
            if not bound:
                out.append(f"{block.type} «{block.data['title']}» после источника: укажите source: id или free: true")
            continue
        for n, it in enumerate(block.data["items"], 1):
            meta = it.get("meta") or {}
            if not (bound or meta.get("source") or meta.get("free")):
                text = it.get("q") or it.get("say") or it.get("es") or ""
                out.append(f"{block.type}, вопрос {n} «{plain(text)[:40]}» после источника: укажите source: id или free: true")
    if seen_source:
        for n, q in enumerate(lesson.quiz, 1):
            if not (q.meta.get("source") or q.meta.get("free")):
                out.append(f"тест, вопрос {n} «{plain(q.question)[:40]}»: в уроке есть источник — укажите source: id или free: true")
    if lesson.scripted and not any(b.type == "recap" for b in lesson.blocks):
        asked = _asked_texts(lesson)
        conj = {b.data["verb"].lower(): b.data["forms"] for b in lesson.blocks if b.type == "conjugation"}
        for item in lesson.vocab:
            if item.srs and not _covered(item, asked, conj.get(item.es.lower(), [])):
                out.append(f"слово «{item.es}» не проверяется ни одним заданием: добавьте задание или блок recap")
    return out


def _asked_texts(lesson: Lesson) -> list[str]:
    """Тексты, которые урок спрашивает: верные варианты и вопросы, ответы ввода, пары, группы, фразы."""
    out = []
    for block in lesson.blocks:
        if block.meta.get("bank"):   # банк повторения в уроке не показывается — слово урока он не проверяет
            continue
        d = block.data
        if block.type == "choose":
            # реплика собеседника тоже проверяет слово: чтобы ответить на «¿Quién es?», его надо понять
            out += [t for it in d["items"] for t in (it["q"], it["options"][0], it["say"], *(line[1] for line in it["lines"]))]
        elif block.type == "write":
            out += [t for it in d["items"] for t in (it["q"], *it["answers"], it["say"])]
        elif block.type == "match":
            out += [t for pair in d["pairs"] for t in pair]
        elif block.type == "sort":
            out += [x for _, xs in d["groups"] for x in xs]
        elif block.type == "build":
            out += [it["es"] for it in d["items"]]
        elif block.type == "compose":
            out += [it["q"] for it in d["items"]]
        elif block.type == "chat":
            for it in d["items"]:
                out += [it["line"][1], it["task"]]
                out += [it["es"]] if it["kind"] == "build" else it["answers"] if it["kind"] == "write" else it["options"][:1] if it["kind"] == "choose" else []
            out += [line[1] for line in d["end"]]
    out += [t for q in lesson.quiz for t in (q.question, q.options[q.correct])]
    return [f" {_key(t)} " for t in out if t]


def _covered(item, asked: list[str], conj_forms=()) -> bool:
    """Слово проверяется, если задание спрашивает его само или его форму: soy, eres, es — это ser; mexicana — mexicano/a."""
    strip = lambda t: _key(re.sub(r"^(?:el/la|el|la|los|las|un|una)\s+", "", t.strip(), flags=re.I))
    core = strip(item.es.split("/")[0])
    # «el amigo / la amiga» — обе формы: задание может спрашивать любую
    forms = {core} | {strip(v) for v in re.split(r"\s/\s", item.es)}
    # формы, которые ученик образует по правилам: los ojos — el ojo, lleva — llevar
    forms |= {_key(f) for f in generated_forms(item, frozenset(FEATURES))} | {_key(f) for f in conj_forms}
    forms |= ({_key(f) for f in item.base_forms()} if item.pos in ("verb", "adj") else set()) | {_key(f) for f in item.extra_forms}
    forms |= {f[:-3] + " del" for f in forms if f.endswith(" de")}   # encima de → encima del sofá
    if re.search(r"\.\.\.|…", item.es):   # фраза с пропуском: «¿Cómo se dice... en español?» — все её части
        parts = [_key(p) for p in re.split(r"\.\.\.|…", item.es) if _key(p)]
        if any(all(f" {p} " in t for p in parts) for t in asked):
            return True
    return any(f and any(f" {f} " in t for t in asked) for f in forms)


def _screens(lesson: Lesson) -> list[list]:
    """Экраны объяснения перестроенного урока: блоки подряд между заданиями; slide: new — новый экран."""
    screens, cur = [], []
    for block in lesson.blocks:
        if block.type in GRADED_BLOCKS | {"learn", "recap", "review", "exercise"}:
            if cur:
                screens.append(cur)
            cur = []
            continue
        if (block.meta.get("slide") == "new" or block.type == "mission") and cur:   # как authoredScreens на странице
            screens.append(cur)
            cur = []
        cur.append(block)
    if cur:
        screens.append(cur)
    return screens


def _visible(block) -> str:
    d = block.data
    if isinstance(d, str):
        return plain(d)
    if isinstance(d, list):
        return " ".join(plain(x) for x in d)
    if block.type == "dialogue":
        return " ".join(plain(es) for _, es, _ in d["lines"])
    if block.type == "examples":
        return " ".join(plain(ex.es) + " " + plain(ex.ru) for ex in d["items"])
    if block.type == "table":
        return " ".join(plain(c) for row in d["rows"] for c in row)
    if block.type == "compare":
        return " ".join(plain(x) for c in d["cards"] for x in (c["head"], c["label"], c["text"], *[e for p in c["ex"] for e in p])) + plain(d.get("lead") or "") + plain(d.get("note") or "")
    if block.type in ("mission", "more"):
        return plain(d["title"]) + " " + plain(d["text"])
    if block.type == "reading":
        return plain(d["text"])
    if block.type == "conjugation":
        return " ".join(d["forms"])
    return ""


SCREEN_MAX, SCREEN_MIN = 900, 25


def screen_warnings(course: Course) -> list[Issue]:
    """Предупреждения о длине экранов перестроенных уроков (не ошибки: автор решает по карте слайдов)."""
    out = []
    for lesson in course.lessons:
        if lesson.version < 2 or not lesson.scripted:
            continue
        for n, sc in enumerate(_screens(lesson), 1):
            # «Подробнее» свёрнуто и в длину экрана не входит.
            text = " ".join(_visible(b) for b in sc if b.type != "more")
            first = plain(str(sc[0].data))[:30] if isinstance(sc[0].data, str) else sc[0].type
            if len(text) > SCREEN_MAX:
                out.append(Issue(lesson, f"экран {n} ({first}…) — {len(text)} знаков: разделите (slide: new) или сократите"))
            if all(b.type == "header" for b in sc) or len(text) < SCREEN_MIN:
                out.append(Issue(lesson, f"экран {n} ({first}) почти пустой: объедините с соседним"))
    return out


def check_lesson(lesson: Lesson, lexicon: Lexicon, skills: dict | None = None, index: dict | None = None) -> list[Issue]:
    issues = [Issue(lesson, msg) for block in lesson.blocks for msg in _block_issues(lesson, block) + _img_issues(block)]
    issues += [Issue(lesson, msg) for msg in _ref_issues(lesson, skills or {}, index or {})]
    if lesson.version >= 2:
        issues += [Issue(lesson, msg) for msg in _strict_issues(lesson)]
    blocks = lesson.blocks
    for k, block in enumerate(blocks):
        if block.type == "mission" and not any(b.type in GRADED_BLOCKS for b in blocks[k + 1:]):
            issues.append(Issue(lesson, "mission: после миссии нужно хотя бы одно задание"))
        if block.type == "more" and (k == 0 or blocks[k - 1].type in GRADED_BLOCKS | {"learn", "exercise", "mission"}):
            issues.append(Issue(lesson, "more: свёрнутое пояснение должно идти сразу после объяснения, которое оно дополняет "
                                        "(после задания или порции слов оно встанет отдельным экраном)"))
    if not lesson.scripted:
        return issues
    by_es = {item.es: item for item in lesson.vocab}
    placed: dict[str, int] = {}
    for k, block in enumerate(blocks):
        if block.type != "learn":
            continue
        for es in block.data:
            if es not in by_es:
                issues.append(Issue(lesson, f"learn: «{es}» нет среди слов урока (vocab)"))
            elif es in placed:
                issues.append(Issue(lesson, f"learn: слово «{es}» стоит в двух порциях"))
            else:
                placed[es] = k
    for item in lesson.vocab:
        if item.es not in placed:
            issues.append(Issue(lesson, f"learn: слово «{item.es}» не стоит ни в одной порции"))
    # Задание не спрашивает слово урока до его карточки. Формы, известные до урока, не в счёт:
    # «un» из прошлых уроков можно спрашивать и до карточки «un / una».
    before = lexicon.known_at[lesson.index - 1] if lesson.index else frozenset()
    features = lexicon.features_at[lesson.index]
    forms = {es: (item.base_forms() | generated_forms(item, features)) - before for es, item in by_es.items()}
    for k, block in enumerate(blocks):
        if block.type not in GRADED_BLOCKS | {"exercise"}:
            continue
        later = {es for es, at in placed.items() if at > k}
        shown = set().union(*(forms[es] for es, at in placed.items() if at < k))   # «el» уже пришло с «el taxi»
        used = {tok for text in _graded_texts(block) for tok in _tokens(text)} - shown
        for es in sorted(later):
            hit = sorted(used & forms[es])
            if hit:
                issues.append(Issue(lesson, f"{block.type}: задание спрашивает «{hit[0]}» раньше карточки слова «{es}»"))
    return issues


def _skill_material(course: Course) -> list[str]:
    """У каждого навыка, который ставят заданиям, есть хотя бы одно самостоятельное задание: его и повторяем."""
    used: dict[str, bool] = {}
    for lesson in course.lessons:
        for k, block, meta, _ in _tasks(lesson):
            tags = meta.get("skill") or block.meta.get("skill") or []
            # открытые задания (письмо, разговор) в повторение навыков не идут: материалом не считаются
            free = block.type not in OPEN_BLOCKS and not (meta.get("source") or (block.meta.get("source") and not meta.get("free")))
            for tag in tags:
                used[tag] = used.get(tag, False) or free
    return [f"skills.yaml: у навыка «{tag}» нет ни одного самостоятельного задания (без source) — повторять нечего"
            for tag, ok in sorted(used.items()) if not ok]


def check(course: Course, lexicon: Lexicon | None = None) -> list[Issue]:
    """Проверки сценариев всех уроков сайта."""
    lexicon = lexicon or Lexicon(course)
    index = {lesson.id: lesson.index for lesson in course.lessons}
    issues = [issue for lesson in course.lessons for issue in check_lesson(lesson, lexicon, course.skills, index)]
    if course.lessons:
        issues += [Issue(course.lessons[0], msg) for msg in _skill_material(course)]
    return issues


def channel_issues(course: Course) -> list[Issue]:
    """Блоки сайта в уроках канала: канал их не покажет."""
    return [Issue(lesson, f"блок {block.type} есть только на сайте (content/site), в канале его не показать")
            for lesson in course.lessons for block in lesson.blocks if block.type in SITE_ONLY_BLOCKS]


__all__ = ["check", "check_lesson", "channel_issues", "lesson_texts", "screen_warnings"]
