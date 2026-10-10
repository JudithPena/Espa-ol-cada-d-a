"""Морфология испанского языка уровня A0–A1.

Модуль умеет образовывать формы слов, которые нужны валидатору словаря:
множественное число существительных, род и число прилагательных,
спряжение глаголов в настоящем времени (включая отклоняющиеся),
герундий и причастие. Правила покрывают лексику курса; для редких
исключений в словаре можно указать формы явно.
"""

from __future__ import annotations

import re

VOWELS = "aeiouáéíóúü"
ACCENTED = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"}

PERSONS = (
    "yo",
    "tú",
    "él/ella/usted",
    "nosotros/-as",
    "vosotros/-as",
    "ellos/ellas/ustedes",
)

ENDINGS = {
    "ar": ("o", "as", "a", "amos", "áis", "an"),
    "er": ("o", "es", "e", "emos", "éis", "en"),
    "ir": ("o", "es", "e", "imos", "ís", "en"),
}

# Лица, в которых меняется корень у глаголов типа querer/poder/pedir.
STEM_PERSONS = (0, 1, 2, 5)

REFLEXIVE_PRONOUNS = ("me", "te", "se", "nos", "os")


def _v(**kw) -> dict:
    if "present" in kw:
        kw["present"] = kw["present"].split()
    return kw


# Неправильные и отклоняющиеся глаголы. Для возвратных глаголов
# (levantarse, acostarse) ищется основа без -se.
VERBS: dict[str, dict] = {
    # полностью неправильные в настоящем времени
    "ser": _v(present="soy eres es somos sois son", gerund="siendo", participle="sido"),
    "estar": _v(present="estoy estás está estamos estáis están"),
    "ir": _v(present="voy vas va vamos vais van", gerund="yendo", participle="ido"),
    "haber": _v(present="he has ha hemos habéis han"),
    "dar": _v(present="doy das da damos dais dan"),
    "ver": _v(present="veo ves ve vemos veis ven", participle="visto"),
    "oír": _v(present="oigo oyes oye oímos oís oyen", gerund="oyendo", participle="oído"),
    "reír": _v(present="río ríes ríe reímos reís ríen", gerund="riendo", participle="reído"),
    # неправильная только форма yo
    "saber": _v(yo="sé"),
    "conocer": _v(yo="conozco"),
    "parecer": _v(yo="parezco"),
    "conducir": _v(yo="conduzco"),
    "traducir": _v(yo="traduzco"),
    "ofrecer": _v(yo="ofrezco"),
    "hacer": _v(yo="hago", participle="hecho"),
    "poner": _v(yo="pongo", participle="puesto"),
    "salir": _v(yo="salgo"),
    "traer": _v(yo="traigo"),
    "caer": _v(yo="caigo"),
    "coger": _v(yo="cojo"),
    # изменение корня + неправильная форма yo
    "tener": _v(stem="ie", yo="tengo"),
    "venir": _v(stem="ie", yo="vengo"),
    "decir": _v(stem="i", yo="digo", participle="dicho"),
    "seguir": _v(stem="i", yo="sigo"),
    "elegir": _v(stem="i", yo="elijo"),
    # e > ie
    **{
        v: _v(stem="ie")
        for v in (
            "querer pensar empezar comenzar cerrar entender perder preferir sentir "
            "despertar sentar nevar merendar recomendar mentir divertir calentar"
        ).split()
    },
    # o > ue, u > ue
    **{
        v: _v(stem="ue")
        for v in (
            "dormir costar contar encontrar recordar probar acostar llover doler "
            "soñar mover almorzar jugar volar mostrar"
        ).split()
    },
    "poder": _v(stem="ue", gerund="pudiendo"),
    "volver": _v(stem="ue", participle="vuelto"),
    "devolver": _v(stem="ue", participle="devuelto"),
    "morir": _v(stem="ue", participle="muerto"),
    # e > i
    **{v: _v(stem="i") for v in "pedir repetir servir vestir".split()},
    # неправильные причастия
    "escribir": _v(participle="escrito"),
    "abrir": _v(participle="abierto"),
    "romper": _v(participle="roto"),
    "descubrir": _v(participle="descubierto"),
}

_VERB_RE = re.compile(r"^[a-záéíóúñü]+(ar|er|ir|ír)(se)?$")
# Слова на -ar/-er/-ir, которые не являются глаголами.
NOT_VERBS = {
    "ayer", "mujer", "mayor", "mejor", "peor", "menor", "lugar", "bar", "mar",
    "hogar", "señor", "color", "favor", "por", "par", "azúcar", "suéter",
    "placer", "alfiler", "taller", "chófer", "póster", "máster", "cráter",
}


def strip_accents(word: str) -> str:
    return "".join(ACCENTED.get(ch, ch) for ch in word)


def _vowel_groups(word: str) -> list[tuple[int, int]]:
    """Границы групп гласных (грубое приближение к слогам)."""
    groups, start = [], None
    for i, ch in enumerate(word.lower()):
        if ch in VOWELS:
            if start is None:
                start = i
        elif start is not None:
            groups.append((start, i))
            start = None
    if start is not None:
        groups.append((start, len(word)))
    return groups


def syllable_count(word: str) -> int:
    return max(1, len(_vowel_groups(word)))


def _final_accent_index(word: str) -> int | None:
    """Индекс ударной гласной со знаком ударения, если она в последнем слоге."""
    groups = _vowel_groups(word)
    if not groups:
        return None
    start, end = groups[-1]
    for i in range(start, end):
        if word[i] in ACCENTED:
            return i
    return None


def drop_final_accent(word: str) -> str:
    """canción → cancion, inglés → ingles (перед окончанием -es / -a)."""
    i = _final_accent_index(word)
    if i is None:
        return word
    return word[:i] + ACCENTED[word[i]] + word[i + 1:]


def plural(word: str) -> str:
    """Множественное число существительного или прилагательного."""
    if " " in word:
        # fin de semana → fines de semana, café con leche → cafés con leche
        head, rest = word.split(" ", 1)
        return plural(head) + " " + rest
    last = word[-1]
    if last in "aeiouáéó":
        return word + "s"
    if last in "íú":
        return word + "s"
    if last == "z":
        return word[:-1] + "ces"
    if last in "sx":
        if syllable_count(word) > 1 and _final_accent_index(word) is None:
            return word  # el lunes → los lunes
        return drop_final_accent(word) + "es"
    return drop_final_accent(word) + "es"


def adjective_forms(spec: str) -> list[str]:
    """«alto/a» → [alto, alta]; «inglés/a» → [inglés, inglesa]; «grande» → [grande]."""
    if "/" not in spec:
        return [spec]
    masc, suffix = (part.strip() for part in spec.split("/", 1))
    if suffix != "a":
        return [masc, suffix]  # полная форма: «joven/jóvenes» не используется
    if masc.endswith("o"):
        return [masc, masc[:-1] + "a"]
    if masc[-1] in VOWELS:
        return [masc, masc + "a"]
    return [masc, drop_final_accent(masc) + "a"]


def is_verb(word: str) -> bool:
    return bool(_VERB_RE.match(word)) and word not in NOT_VERBS


def split_verb(infinitive: str) -> tuple[str, str, str, bool]:
    """Возвращает (основа без -se, спряжение ar/er/ir, корень, возвратный ли)."""
    reflexive = infinitive.endswith("se") and is_verb(infinitive[:-2])
    base = infinitive[:-2] if reflexive else infinitive
    conj = base[-2:].replace("í", "i")
    return base, conj, base[:-2], reflexive


def verb_info(infinitive: str) -> dict:
    base, _, _, _ = split_verb(infinitive)
    return VERBS.get(base, {})


def apply_stem_change(stem: str, change: str) -> str:
    if change == "ue":
        i = stem.rfind("o")
        if i < 0:  # jugar → juego
            i = stem.rfind("u")
        return stem[:i] + "ue" + stem[i + 1:]
    i = stem.rfind("e")
    if i < 0:
        return stem
    return stem[:i] + ("ie" if change == "ie" else "i") + stem[i + 1:]


def present(infinitive: str, info: dict | None = None) -> list[str]:
    """Шесть форм настоящего времени: yo, tú, él, nosotros, vosotros, ellos."""
    info = verb_info(infinitive) if info is None else info
    if info.get("present"):
        return list(info["present"])
    _, conj, stem, _ = split_verb(infinitive)
    change = info.get("stem")
    forms = []
    for person, ending in enumerate(ENDINGS[conj]):
        s = apply_stem_change(stem, change) if change and person in STEM_PERSONS else stem
        forms.append(s + ending)
    if info.get("yo"):
        forms[0] = info["yo"]
    return forms


def present_group(infinitive: str, info: dict | None = None) -> str:
    """К какой грамматической теме относится спряжение глагола в настоящем времени.

    regular_ar / regular_er_ir — правильные (в том числе с особой формой yo),
    stem — с чередованием в корне, irregular — полностью неправильные.
    """
    info = verb_info(infinitive) if info is None else info
    if info.get("present"):
        return "irregular"
    if info.get("stem"):
        return "stem"
    _, conj, _, _ = split_verb(infinitive)
    return "regular_ar" if conj == "ar" else "regular_er_ir"


def gerund(infinitive: str, info: dict | None = None) -> str:
    info = verb_info(infinitive) if info is None else info
    if info.get("gerund"):
        return info["gerund"]
    _, conj, stem, _ = split_verb(infinitive)
    if conj == "ar":
        return stem + "ando"
    if stem and stem[-1] in "aeiou":
        return stem + "yendo"  # leer → leyendo
    change = info.get("stem")
    if conj == "ir" and change in ("ie", "i"):
        i = stem.rfind("e")
        stem = stem[:i] + "i" + stem[i + 1:]  # pedir → pidiendo
    elif conj == "ir" and change == "ue":
        i = stem.rfind("o")
        stem = stem[:i] + "u" + stem[i + 1:]  # dormir → durmiendo
    return stem + "iendo"


def participle(infinitive: str, info: dict | None = None) -> str:
    info = verb_info(infinitive) if info is None else info
    if info.get("participle"):
        return info["participle"]
    _, conj, stem, _ = split_verb(infinitive)
    if conj == "ar":
        return stem + "ado"
    if stem and stem[-1] in "aeo":
        return stem + "ído"  # leer → leído
    return stem + "ido"


def reflexive_infinitives(infinitive: str) -> list[str]:
    """levantarse → levantarme, levantarte, levantarse, levantarnos, levantaros."""
    base, _, _, reflexive = split_verb(infinitive)
    if not reflexive:
        return []
    return [base + p for p in REFLEXIVE_PRONOUNS]
