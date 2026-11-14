"""Юнит 69: покрытие источника, контракт данных, сохранность предыдущих юнитов."""
import hashlib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 69
# Сколько пунктов в каждом упражнении страницы-источника: NN.1, NN.2, …
SOURCE_ITEMS = [4, 7, 3, 4]
# Пункты источника, которые не стали вопросами: причина из реестра в отчёте юнита.
NOT_TRANSFERRED = {"69.1.1": "Заполненный образец по рисунку (Van a jugar al tenis); рисунки не переносим, образец упражнения показан на пункте 69.2.1.", "69.2.1": "Заполненный образец источника сохранён в preview упражнения 69.1.", "69.4.1": "Заполненный образец источника сохранён в preview упражнения 69.3."}
PLAIN_TEXT = ("prompt", "context", "explain", "translation", "answerHint")


def unit():
    return next(u for u in load_grammar() if u["number"] == NUMBER)


def test_previous_units_are_untouched():
    before = json.loads(Path(f"tests/data/grammar_before_unit{NUMBER}.json").read_text(encoding="utf-8"))
    assert len(before) == len([p for p in GRAMMAR.glob("[0-9]*.json") if int(p.name[:3]) < NUMBER])
    for name, digest in before.items():
        data = (GRAMMAR / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == digest, name


def test_every_source_item_is_accounted_for():
    refs = [q["sourceRef"] for g in unit()["exercises"] for q in g["questions"]]
    assert all(refs), "у каждого вопроса упражнения есть sourceRef"
    used = [r for r in refs if r != "extra"]
    assert len(used) == len(set(used)), "один пункт источника не переносится дважды"
    covered = {re.sub(r"[a-z]$", "", r) for r in used}
    expected = {f"{NUMBER}.{g}.{i}" for g, count in enumerate(SOURCE_ITEMS, 1) for i in range(1, count + 1)}
    assert not covered & set(NOT_TRANSFERRED)
    assert covered | set(NOT_TRANSFERRED) == expected
    assert all(len(reason) >= 15 for reason in NOT_TRANSFERRED.values())


def test_unit_contract():
    u = unit()
    assert u["id"] == next(GRAMMAR.glob(f"{NUMBER:03d}_*.json")).stem
    assert u["learningOrder"][-1] == "summary"
    for section in u["sections"]:
        check = section["check"]
        assert check["title"] == "Мини-проверка" and check["instruction"].strip()
        assert len(check["questions"]) == 3 and "inputFormat" not in check
        for q in check["questions"]:
            assert len(q.get("options", [])) >= 2 and set(q["options"]) - set(q["answers"]), q["prompt"]
    for group in [s["check"] for s in u["sections"]] + u["exercises"]:
        for q in group["questions"]:
            assert q.get("context") and q.get("learningAction")
            for field in PLAIN_TEXT:
                assert "`" not in q.get(field, "") and "**" not in q.get(field, ""), (group["id"], field)
            if q.get("options"):
                assert 2 <= len(q["options"]) <= 6
            typed = not q.get("options") and not q.get("tiles") and not q.get("guidedGaps")
            if typed:
                fmt = q.get("inputFormat") or group.get("inputFormat")
                assert fmt and fmt["instruction"] and fmt["placeholder"], group["id"]
                assert "".join(q["inputChars"]) == "áéíóúüñ"
                assert q.get("accentPolicy") or group.get("accentPolicy"), "режим ударений задан явно"
    for group in u["exercises"]:
        assert group["theorySections"] and 3 <= len(group["questions"]) <= 15
        assert group["title"].startswith(group["id"] + " · ")


def test_report_exists():
    assert Path(f"docs/grammar_units/{NUMBER:02d}.md").exists()

def by_ref(ref):
    return next(q for g in unit()["exercises"] for q in g["questions"] if q["sourceRef"] == ref)


def test_both_pronoun_positions_are_accepted():
    assert by_ref("69.1.2")["answers"] == ["van a bañarse", "se van a bañar"]
    assert by_ref("69.2.3")["answers"] == ["Vamos a acostarnos", "Nos vamos a acostar"]
    assert by_ref("69.3.1c")["answers"] == ["se van a alojar", "van a alojarse"]


def test_printed_pronouns_are_not_repeated():
    for ref in ("69.3.1d", "69.3.2c", "69.3.2d"):
        q = by_ref(ref)
        assert all(not a.split()[0] in ("lo", "le") for a in q["answers"]), ref


def test_people_and_formats():
    assert by_ref("69.3.3c")["answers"] == ["vais a ir"]
    qs = [q for g in unit()["exercises"] for q in g["questions"]]
    assert len(qs) == 27
    assert not any(q.get("image") for q in qs)
