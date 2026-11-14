"""Regression of stage-3 accent policies without mutating frozen lesson files."""
import json
from pathlib import Path

import pytest

from espanol.grammar import GRAMMAR, load_grammar
from espanol.grammar_quality import breaking_findings, schema_validator, structure_unit

POLICIES=GRAMMAR / "accent_policies.json"


def test_sidecar_is_loaded_in_memory_without_modifying_any_lesson_bytes():
    source={p.name:p.read_bytes() for p in GRAMMAR.glob("[0-9]*.json")}
    units=load_grammar()
    catalog=json.loads(POLICIES.read_text(encoding="utf-8"))
    assert len(units)==64
    assert set(catalog)=={u["id"] for u in units if u["id"] in catalog}
    count=0
    for u in units:
        group_map={g["id"]:g for g in [s["check"] for s in u["sections"]]+u["exercises"]}
        for group_id,question_map in catalog.get(u["id"],{}).items():
            assert group_id in group_map
            for index,p in question_map.items():
                q=group_map[group_id]["questions"][int(index)]
                assert q["answers"][0]==p["answer"]
                for key in ("accentPolicy", "accentContrasts", "normalize", "gapAnswers"):
                    if key in p:
                        assert q[key] == p[key]
                count+=1
    assert count>=21
    assert source=={p.name:p.read_bytes() for p in GRAMMAR.glob("[0-9]*.json")}


def test_sidecar_augmented_data_remain_valid_under_public_json_schema():
    validator=schema_validator()
    for unit in load_grammar():
        issues=breaking_findings(structure_unit(unit,"in-memory.json",validator))
        assert not issues,[(x.rule,x.message) for x in issues]


@pytest.mark.parametrize("mode,pairs,issue",[
    ("contextual",None,"ACCENT_CONTEXT_MISSING"),
    ("soft",None,"ACCENT_POLICY_CONFLICT"),
])
def test_inconsistent_accent_rules_are_blocked(mode,pairs,issue):
    unit=load_grammar()[0]
    q=unit["exercises"][0]["questions"][0]
    q["accentPolicy"]=mode
    if mode=="soft":
        q["accentSensitive"]=True
    else:
        q.pop("accentContrasts",None)
    found=structure_unit(unit,"fixture.json",schema_validator())
    assert issue in {x.rule for x in found}


def test_unrelated_external_grammar_directory_does_not_inherit_site_policy(tmp_path):
    minimal={
        "id":"test_external",
        "number":1,
        "title":"Fixture",
        "sections":[],
        "exercises":[{"id":"fixture.1","title":"Test","instruction":"Answer",
                      "questions":[{"prompt":"¿Qué es?","answers":["casa"],"explain":"Sustantivo."}]}]
    }
    (tmp_path/"001_fixture.json").write_text(json.dumps(minimal,ensure_ascii=False),encoding="utf8")
    [unit]=load_grammar(tmp_path)
    assert "accentPolicy" not in unit["exercises"][0]["questions"][0]
