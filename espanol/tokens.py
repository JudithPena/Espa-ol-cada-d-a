"""Выделение испанских слов из смешанного русско-испанского текста."""

from __future__ import annotations

import re

LATIN = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"

# Слово из латинских букв, не примыкающее к цифрам, кириллице и дефису:
# «A1» и окончания вида «-ar» не считаются испанскими словами.
WORD_RE = re.compile(rf"(?<![\w\-])([{LATIN}]+)(?![\w\-])")
# Запись рода «alto/a», «nosotros/-as» — окончание после косой черты не слово.
GENDER_SUFFIX_RE = re.compile(r"/-?(?:a|as|os)(?![\w])")
# Слово, в котором смешаны латиница и кириллица, — почти всегда опечатка.
MIXED_RE = re.compile(rf"(?<!\w)(?=\w*[{LATIN}])(?=\w*[А-Яа-яЁё])\w+")
PUNCT_RE = re.compile(r"[¿?¡!.,;:«»\"“”()\[\]…—–\-/]+")


def spanish_words(text: str) -> list[str]:
    """Испанские слова в исходном регистре, в порядке появления."""
    return WORD_RE.findall(GENDER_SUFFIX_RE.sub("", text))


def mixed_script_words(text: str) -> list[str]:
    return MIXED_RE.findall(text)


def normalize_phrase(text: str) -> str:
    """«¡Buenos días!» → « buenos días » — для поиска фраз в тексте."""
    text = PUNCT_RE.sub(" ", GENDER_SUFFIX_RE.sub("", text.lower()))
    return " " + " ".join(text.split()) + " "
