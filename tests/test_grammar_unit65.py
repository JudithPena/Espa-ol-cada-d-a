"""Юнит NN: покрытие источника, контракт данных, сохранность предыдущих юнитов."""
import hashlib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 65
# Сколько пунктов в каждом упражнении страницы-источника: NN.1, NN.2, …
SOURCE_ITEMS = [6, 7, 6]
# Пункты источника, которые не стали вопросами: причина из реестра в отчёте юнита.
NOT_TRANSFERRED = {"65.1.1": "Заполненный образец источника сохранён в preview упражнения 65.1.", "65.3.1": "Заполненный образец источника сохранён в preview упражнения 65.3."}
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
    covered = set()
    for r in used:
        base, *more = re.sub(r"[a-z]$", "", r).split("+")
        covered.add(base)
        covered.update(base.rsplit(".", 1)[0] + "." + n for n in more)
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


def test_witness_forms():
    assert by_ref("65.1.3")["answers"] == ["estaba hablando estaba leyendo"]
    assert by_ref("65.1.6")["answers"] == ["estaban aparcando estaba echando"]
    assert by_ref("65.1.4")["answers"] == ["Estábamos mirando"]


def test_simple_imperfect_is_accepted_where_normative():
    assert by_ref("65.2.1")["answers"] == ["estaba hablando", "hablaba"]
    assert by_ref("65.2.6")["answers"] == ["Me estaba duchando", "Estaba duchándome", "Me duchaba"]
    assert set(by_ref("65.3.3")["answers"]) == {"Estaban viajando", "Viajaban"}


def test_state_verbs_take_simple_imperfect():
    for ref, answer in [("65.3.2", "ibas"), ("65.3.4a", "llevaba"), ("65.3.4b", "Parecía"), ("65.3.5", "venían"), ("65.3.6", "necesitaba")]:
        q = by_ref(ref)
        assert q["answers"] == [answer] and any(o.startswith(("estaba", "Estaba")) for o in q["options"])


def test_variety():
    qs = [q for g in unit()["exercises"] for q in g["questions"]]
    assert len(qs) == 21 and sum(bool(q.get("tiles")) for q in qs) == 2
    assert len({q["learningAction"] for q in qs}) >= 3
