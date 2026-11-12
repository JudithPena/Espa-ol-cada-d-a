"""Юнит 53: покрытие источника, контракт данных, сохранность предыдущих юнитов."""
import hashlib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 53
# Сколько пунктов в каждом упражнении страницы-источника: NN.1, NN.2, …
SOURCE_ITEMS = [5, 12, 8]
# Пункты источника, которые не стали вопросами: причина из реестра в отчёте юнита.
NOT_TRANSFERRED = {"53.1.1": "заполненный образец Arturo se despierta показан на вступительном экране 53.2",
                   "53.2.1": "заполненный образец Javi se lava показан на вступительном экране 53.1"}
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


def test_pronoun_paradigms_and_stem_changes():
    u = unit()
    assert all(g["accentPolicy"] == "strict" for g in u["exercises"])
    rows = u["sections"][1]["table"]["rows"]
    assert [r[0] for r in rows][4] == "nosotros, nosotras"
    assert rows[0][1:] == ["me divierto", "me visto", "me acuesto", "me pongo"]
    assert rows[4][1:] == ["nos divertimos", "nos vestimos", "nos acostamos", "nos ponemos"]
    assert rows[5][1:] == ["os divertís", "os vestís", "os acostáis", "os ponéis"]
    text = json.dumps(u, ensure_ascii=False)
    for wrong in ("nos acuestamos", "os divirtís", "me ponio", "se no ", "nos no "):
        assert wrong not in text.replace("Nos no aburrimos", ""), wrong


def test_book_items_keep_negatives_and_dialogue_pairs():
    assert by_ref("53.2.4")["answers"] == ["no se afeita"]
    assert by_ref("53.2.8")["answers"] == ["No se atreve"]
    assert by_ref("53.3.1")["answers"] == ["Me levanto"]
    assert by_ref("53.3.8")["answers"] == ["se acuestan Nos acostamos"]
    assert by_ref("53.3.4")["answers"] == ["os ponéis Nos ponemos"]
    # Irregular verbs are practised only after their theory block.
    for ref in ("53.1.4", "53.1.5", "53.2.2", "53.2.6", "53.2.11"):
        group = next(g for g in unit()["exercises"] if any(q["sourceRef"] == ref for q in g["questions"]))
        assert 1 in group["theorySections"], ref


def test_report_exists():
    assert Path(f"docs/grammar_units/{NUMBER:02d}.md").exists()
