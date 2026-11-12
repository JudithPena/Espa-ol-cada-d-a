"""Морфология испанского языка уровня A0–A2.

Модуль умеет образовывать формы слов, которые нужны валидатору словаря:
множественное число существительных, род и число прилагательных,
спряжение глаголов в настоящем времени (включая отклоняющиеся),
герундий и причастие, а для A2 — pretérito indefinido, pretérito imperfecto
и утвердительный императив. Правила покрывают лексику курса; для редких
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
    for key in ("present", "preterite", "imperfect"):
        if key in kw:
            kw[key] = kw[key].split()
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
    "reconocer": _v(yo="reconozco"),
    "nacer": _v(yo="nazco"),
    "crecer": _v(yo="crezco"),
    "agradecer": _v(yo="agradezco"),
    "desaparecer": _v(yo="desaparezco"),
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

_VERB_RE = re.compile(r"^[a-záéíóúñü]*(ar|er|ir|ír)(se)?$")  # * — чтобы «ir» тоже был глаголом
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


# ---------------------------------------------------------------- A2: прошедшие времена и императив

PRETERITE_ENDINGS = {
    "ar": ("é", "aste", "ó", "amos", "asteis", "aron"),
    "er": ("í", "iste", "ió", "imos", "isteis", "ieron"),
    "ir": ("í", "iste", "ió", "imos", "isteis", "ieron"),
}
# Особые основы indefinido (тема preterite_irregular): окончания -e, -iste, -o, -imos, -isteis, -ieron без ударений.
PRETERITE_STEMS = {
    "estar": "estuv", "tener": "tuv", "poder": "pud", "poner": "pus", "saber": "sup", "andar": "anduv",
    "venir": "vin", "querer": "quis", "hacer": "hic", "haber": "hub", "caber": "cup",
    "decir": "dij", "traer": "traj", "conducir": "conduj", "traducir": "traduj", "producir": "produj",
}
PRETERITE_FULL = {
    "ser": "fui fuiste fue fuimos fuisteis fueron".split(),
    "ir": "fui fuiste fue fuimos fuisteis fueron".split(),
    "dar": "di diste dio dimos disteis dieron".split(),
    "ver": "vi viste vio vimos visteis vieron".split(),
}
IMPERFECT_FULL = {
    "ser": "era eras era éramos erais eran".split(),
    "ir": "iba ibas iba íbamos ibais iban".split(),
    "ver": "veía veías veía veíamos veíais veían".split(),
}
IMPERATIVE_TU = {
    "decir": "di", "hacer": "haz", "ir": "ve", "poner": "pon", "salir": "sal", "ser": "sé", "tener": "ten", "venir": "ven",
}
# Формы usted (настоящее сослагательного), которые не выводятся из формы yo.
IMPERATIVE_USTED = {"ir": "vaya", "ser": "sea", "estar": "esté", "dar": "dé", "saber": "sepa", "haber": "haya", "ver": "vea"}


def is_preterite_irregular(infinitive: str) -> bool:
    base = split_verb(infinitive)[0]
    return base in PRETERITE_STEMS or base in PRETERITE_FULL


def _spell_e(stem: str) -> str:
    """Основа перед -e / -é: busc → busqu, lleg → llegu, empez → empec, averigu → averigü."""
    if stem.endswith("c"):
        return stem[:-1] + "qu"
    if stem.endswith("gu"):
        return stem[:-2] + "gü"
    if stem.endswith("g"):
        return stem + "u"
    if stem.endswith("z"):
        return stem[:-1] + "c"
    return stem


def _third_stem(stem: str, conj: str, change: str | None) -> str:
    """Основа 3-го лица indefinido у глаголов на -ir с чередованием: pedir → pid-, dormir → durm-."""
    if conj != "ir" or not change:
        return stem
    if change in ("ie", "i"):
        i = stem.rfind("e")
        return stem if i < 0 else stem[:i] + "i" + stem[i + 1:]
    i = stem.rfind("o")
    return stem if i < 0 else stem[:i] + "u" + stem[i + 1:]


def preterite(infinitive: str, info: dict | None = None) -> list[str]:
    """Шесть форм pretérito indefinido."""
    info = verb_info(infinitive) if info is None else info
    base, conj, stem, _ = split_verb(infinitive)
    if base in PRETERITE_FULL:
        return list(PRETERITE_FULL[base])
    if base in PRETERITE_STEMS:
        st = PRETERITE_STEMS[base]
        third = "hizo" if base == "hacer" else st + "o"
        plural3 = st + ("eron" if st.endswith("j") else "ieron")
        return [st + "e", st + "iste", third, st + "imos", st + "isteis", plural3]
    if base in ("reír", "sonreír"):
        pre = base[:-4]
        return [pre + f for f in ("reí", "reíste", "rio", "reímos", "reísteis", "rieron")]
    if conj == "ar":
        forms = [stem + e for e in PRETERITE_ENDINGS["ar"]]
        forms[0] = _spell_e(stem) + "é"
        return forms
    if stem and stem[-1] in "aeoí" or base in ("oír",) or (stem.endswith("u") and not stem.endswith(("gu", "qu"))):
        # leer → leí, leíste, leyó, leímos, leísteis, leyeron; construir → construyó
        s0 = stem.rstrip("í") if base == "oír" else stem
        strong = s0[-1] in "aeo"
        return [s0 + "í", s0 + ("íste" if strong else "iste"), s0 + "yó", s0 + ("ímos" if strong else "imos"),
                s0 + ("ísteis" if strong else "isteis"), s0 + "yeron"]
    third = _third_stem(stem, conj, info.get("stem"))
    ends = PRETERITE_ENDINGS[conj]
    return [stem + ends[0], stem + ends[1], third + ends[2], stem + ends[3], stem + ends[4], third + ends[5]]


def imperfect(infinitive: str) -> list[str]:
    """Шесть форм pretérito imperfecto."""
    base, conj, stem, _ = split_verb(infinitive)
    if base in IMPERFECT_FULL:
        return list(IMPERFECT_FULL[base])
    if conj == "ar":
        return [stem + e for e in ("aba", "abas", "aba", "ábamos", "abais", "aban")]
    if base in ("oír", "reír", "sonreír"):
        stem = base[:-2]
    return [stem + e for e in ("ía", "ías", "ía", "íamos", "íais", "ían")]


def imperative(infinitive: str, info: dict | None = None) -> list[str]:
    """Утвердительный императив: tú, usted, vosotros, ustedes."""
    info = verb_info(infinitive) if info is None else info
    base, conj, stem, _ = split_verb(infinitive)
    pres = present(base, info)
    tu = IMPERATIVE_TU.get(base, pres[2])
    if base in IMPERATIVE_USTED:
        usted = IMPERATIVE_USTED[base]
    else:
        yo = pres[0]
        root = yo[:-1] if yo.endswith("o") else stem
        usted = (_spell_e(root) + "e") if conj == "ar" else root + "a"
        if conj != "ar" and root.endswith("c") and not yo.endswith("zco"):
            usted = root[:-1] + "za"   # vencer → venza
        if conj != "ar" and root.endswith("gu"):
            usted = root[:-1] + "a"    # seguir: sigo → siga
    ustedes = {"dé": "den", "esté": "estén"}.get(usted, usted + "n")
    vosotros = base[:-1] + "d"
    return [tu, usted, vosotros, ustedes]
