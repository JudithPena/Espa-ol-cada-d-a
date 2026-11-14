"""Юнит 66: источник, структура, прошлое раньше прошлого, варианты."""
import hashlib
import json
import re
from pathlib import Path
from espanol.grammar import GRAMMAR, load_grammar

NUMBER = 66
SOURCE_ITEMS = [5, 9, 5]
NOT_TRANSFERRED = {
    "66.1.1": "Заполненный образец перенесён во вступительный экран 66.1.",
    "66.2.1": "Заполненный образец перенесён во вступительный экран 66.2.",
    "66.3.1": "Заполненный образец перенесён во вступительный экран 66.3.",
}
PLAIN_TEXT = ("prompt", "context", "explain", "translation", "answerHint")
def unit():
    return next(u for u in load_grammar() if u["number"] == NUMBER)
def by_ref(ref):
    return next(q for g in unit()["exercises"] for q in g["questions"] if q["sourceRef"] == ref)

def test_previous_units_unchanged():
    before=json.loads(Path("tests/data/grammar_before_unit66.json").read_text(encoding="utf-8"))
    files=[p for p in GRAMMAR.glob("[0-9]*.json") if int(p.name[:3]) < NUMBER]
    assert len(files)==len(before)==65
    for name, digest in before.items():
        raw=(GRAMMAR/name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(raw).hexdigest()==digest, name

def test_source_all_items_accounted():
    refs=[q["sourceRef"] for g in unit()["exercises"] for q in g["questions"]]
    assert all(refs)
    used=[r for r in refs if r!="extra"]
    assert len(used)==len(set(used))
    expected={f"66.{g}.{i}" for g,n in enumerate(SOURCE_ITEMS,1) for i in range(1,n+1)}
    assert set(used)|set(NOT_TRANSFERRED)==expected
    assert not set(used)&set(NOT_TRANSFERRED)
    assert all(len(reason)>15 for reason in NOT_TRANSFERRED.values())

def test_contract_and_variety():
    u=unit()
    assert u["id"]=="066_habia_trabajado"
    assert u["learningOrder"][-1]=="summary"
    assert len(u["sections"])==4
    assert [len(g["questions"]) for g in u["exercises"]]==[6,10,6]
    assert len(u["summary"]["topicMap"]["cards"])==6
    assert all(len(s["check"]["questions"])==3 for s in u["sections"])
    assert sum(bool(q.get("tiles")) for g in u["exercises"] for q in g["questions"])==3
    assert len({q["learningAction"] for g in u["exercises"] for q in g["questions"]})>=3
    for s in u["sections"]:
        assert s["presentation"] in ("paradigm","comparison","examples")
        assert s["check"]["title"]=="Мини-проверка"
        assert s["check"]["instruction"]
    for g in [*[s["check"] for s in u["sections"]], *u["exercises"]]:
        assert len(g["questions"])>=3
        for q in g["questions"]:
            assert q.get("context") and q.get("learningAction") and q.get("sourceRef")
            assert all("**" not in q.get(f,"") and "`" not in q.get(f,"") for f in PLAIN_TEXT)
            if q.get("options"):
                assert set(q["answers"]) <= set(q["options"])
                assert set(q["options"])-set(q["answers"])
            if not q.get("options") and not q.get("tiles"):
                fmt=q.get("inputFormat") or g.get("inputFormat")
                assert fmt and fmt.get("instruction") and fmt.get("placeholder")
                assert "".join(q["inputChars"])=="áéíóúüñ"
                assert q.get("accentPolicy") or g.get("accentPolicy")
    assert all(g["title"].startswith(g["id"]+" · ") for g in u["exercises"])

def test_key_forms_and_alternatives():
    assert by_ref("66.1.5")["answers"]==["había habido"]
    assert by_ref("66.2.5")["answers"]==["se había teñido el pelo"]
    assert by_ref("66.3.2")["answers"]==["todavía no había recogido","no había recogido todavía"]
    assert by_ref("66.3.4")["answers"]==["todavía no se había vestido","no se había vestido todavía"]
    assert by_ref("66.3.3")["answers"]==["había hecho"]
    assert by_ref("66.3.5")["answers"]==["habían desayunado"]

def test_documented():
    assert Path("docs/grammar_units/66.md").exists()
