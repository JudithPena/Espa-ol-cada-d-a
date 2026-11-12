"""Юнит 52: покрытие источника, контракт данных, сохранность предыдущих юнитов."""
import hashlib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 52
# Сколько пунктов в каждом упражнении страницы-источника: NN.1, NN.2, …
SOURCE_ITEMS = [10, 12, 8]
# Пункты источника, которые не стали вопросами: причина из реестра в отчёте юнита.
NOT_TRANSFERRED = {"52.1.1": "заполненный образец ¿Cuánto tiempo hace que vive usted en Caracas? показан на вступительном экране",
                   "52.2.1": "заполненный образец Lupe conoce a Jaime desde 2001 показан на вступительном экране",
                   "52.3.1": "заполненный образец вопроса ¿Cuánto tiempo hace que conoces a César? — та же модель есть в 52.3.3 и 52.3.8",
                   "52.3.2": "заполненный образец ¿Desde cuándo no fumas? показан на вступительном экране"}
PLAIN_TEXT = ("prompt", "context", "explain", "translation", "answerHint")


def unit():
    return next(u for u in load_grammar() if u["number"] == NUMBER)


def questions():
    return [q for g in unit()["exercises"] for q in g["questions"]]


def by_ref(ref):
    return next(q for q in questions() if q["sourceRef"] == ref)


def test_previous_units_are_untouched():
    before = json.loads(Path(f"tests/data/grammar_before_unit{NUMBER}.json").read_text(encoding="utf-8"))
    assert len(before) == len([p for p in GRAMMAR.glob("[0-9]*.json") if int(p.name[:3]) < NUMBER])
    for name, digest in before.items():
        data = (GRAMMAR / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == digest, name


def test_every_source_item_is_accounted_for():
    refs = [q["sourceRef"] for q in questions()]
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


def test_three_constructions_are_taught_and_practised_in_order():
    u = unit()
    formulas = [s["formulas"][0] for s in u["sections"]]
    assert "desde" in formulas[0] and "desde hace" in formulas[1] and "hace" in formulas[2] and "que" in formulas[2]
    assert [g["theorySections"][0] for g in u["exercises"]] == [0, 1, 2]
    assert all(g["accentPolicy"] == "strict" for g in u["exercises"])
    assert "Ronaldo" not in json.dumps(u, ensure_ascii=False)


def test_transformations_accept_natural_variants_and_soften_only_unrelated_accents():
    assert "Desde 1999 vivo en Guayaquil." in by_ref("52.2.8")["answers"]
    assert "Hace una hora que estoy buscando mis gafas." in by_ref("52.2.9")["answers"]
    assert set(by_ref("52.3.6")["answers"]) >= {"Cuánto tiempo hace que estudiáis", "Desde cuándo estudiáis"}
    soft = {q["sourceRef"] for g in unit()["exercises"] for q in g["questions"] if q.get("accentPolicy") == "soft"}
    assert soft == {"52.2.4", "52.2.11", "52.2.12"}  # día, móvil, José — not the target forms
    assert by_ref("52.1.10")["answers"] == ["se conocen"]


def test_report_exists():
    assert Path(f"docs/grammar_units/{NUMBER:02d}.md").exists()
